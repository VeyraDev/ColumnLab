from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engine.format.constants import (
    DEFAULT_MAX_ROWS,
    DEFAULT_MIN_ROWS,
    DEFAULT_TARGET_BLOCK_BYTES,
)
from app.engine.types import LogicalType, LogicalTypeId
from app.engine.vectors import NullBitmap, ValueVector


@dataclass(slots=True)
class RowGroupSlice:
    row_group_id: int
    row_start: int
    row_count: int
    columns: dict[str, ValueVector]


@dataclass
class RowGroupBuilder:
    schemas: dict[str, LogicalType]
    target_block_bytes: int = DEFAULT_TARGET_BLOCK_BYTES
    min_rows: int = DEFAULT_MIN_ROWS
    max_rows: int = DEFAULT_MAX_ROWS
    _buffers: dict[str, list[Any]] = field(default_factory=dict)
    _row_start: int = 0
    _next_group_id: int = 0
    _completed: list[RowGroupSlice] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._buffers = {name: [] for name in self.schemas}

    @property
    def total_rows_buffered(self) -> int:
        if not self._buffers:
            return 0
        first = next(iter(self._buffers.values()))
        return len(first)

    def append_row(self, row: dict[str, Any]) -> list[RowGroupSlice]:
        for name, logical_type in self.schemas.items():
            self._buffers[name].append(row.get(name))
        flushed: list[RowGroupSlice] = []
        while self._should_flush(force=False):
            flushed.append(self._flush_current())
        return flushed

    def finish(self) -> list[RowGroupSlice]:
        flushed: list[RowGroupSlice] = []
        while self.total_rows_buffered > 0:
            flushed.append(self._flush_current(force=True))
        return flushed

    def _should_flush(self, *, force: bool) -> bool:
        count = self.total_rows_buffered
        if count == 0:
            return False
        if force:
            return True
        max_estimate = max(_estimate_raw_bytes(self.schemas[name], self._buffers[name]) for name in self.schemas)
        if count >= self.max_rows:
            return True
        if count >= self.min_rows and max_estimate >= self.target_block_bytes:
            return True
        return False

    def _flush_current(self, *, force: bool = False) -> RowGroupSlice:
        count = self.total_rows_buffered
        if count == 0:
            raise ValueError("cannot flush empty row group")
        if not force and count < self.min_rows:
            # flush all remaining at finish
            pass
        take = count
        if not force and count > self.min_rows:
            # keep at least min_rows unless over budget - simplify: flush all buffered when triggered
            take = count
        columns: dict[str, ValueVector] = {}
        for name, logical_type in self.schemas.items():
            values = self._buffers[name][:take]
            columns[name] = ValueVector.from_typed(logical_type, values)
            self._buffers[name] = self._buffers[name][take:]
        slice_ = RowGroupSlice(
            row_group_id=self._next_group_id,
            row_start=self._row_start,
            row_count=take,
            columns=columns,
        )
        self._next_group_id += 1
        self._row_start += take
        self._completed.append(slice_)
        return slice_


def _estimate_raw_bytes(logical_type: LogicalType, values: list[Any]) -> int:
    nulls = NullBitmap.from_flags([v is None for v in values])
    n = len(values)
    tid = logical_type.type_id
    if tid == LogicalTypeId.BOOLEAN:
        body = (n + 7) // 8
    elif tid == LogicalTypeId.UTF8:
        blob = sum(len(v.encode("utf-8")) if isinstance(v, str) else 0 for v in values if v is not None)
        offset_width = 4
        body = 1 + 4 + (n + 1) * offset_width + blob
    else:
        width = logical_type.fixed_width or 8
        body = n * width
    return len(nulls.serialize()) + body


def build_slices_from_columns(
    columns: dict[str, list[Any]],
    *,
    target_block_bytes: int = DEFAULT_TARGET_BLOCK_BYTES,
    min_rows: int = DEFAULT_MIN_ROWS,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> list[RowGroupSlice]:
    if not columns:
        return []
    schemas = {name: _infer_type(values) for name, values in columns.items()}
    lengths = {name: len(values) for name, values in columns.items()}
    if len(set(lengths.values())) != 1:
        raise ValueError("all columns must have the same row count")
    builder = RowGroupBuilder(
        schemas=schemas,
        target_block_bytes=target_block_bytes,
        min_rows=min_rows,
        max_rows=max_rows,
    )
    names = list(columns.keys())
    total = lengths[names[0]]
    flushed: list[RowGroupSlice] = []
    for i in range(total):
        row = {name: columns[name][i] for name in names}
        flushed.extend(builder.append_row(row))
    flushed.extend(builder.finish())
    return flushed


def _infer_type(values: list[Any]) -> LogicalType:
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            return LogicalType.boolean()
        if isinstance(value, int):
            return LogicalType.int64()
        if isinstance(value, float):
            return LogicalType.float64()
        if isinstance(value, str):
            return LogicalType.utf8()
    return LogicalType.int64()
