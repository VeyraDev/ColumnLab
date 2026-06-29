from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.engine.cache.block_cache import BlockCache, CacheKey, get_block_cache
from app.engine.query.pruning import BlockPruneState, BlockPruningEntry


@dataclass(slots=True)
class OperatorMetric:
    operator_id: str
    operator_type: str
    input_rows: int = 0
    output_rows: int = 0
    elapsed_ns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "operator_type": self.operator_type,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "elapsed_ns": self.elapsed_ns,
        }


@dataclass(slots=True)
class ExecutionMetrics:
    scanned_blocks: int = 0
    pruned_blocks: int = 0
    cache_hits: int = 0
    bytes_read: int = 0
    rows_examined: int = 0
    rows_output: int = 0
    compressed_operator_blocks: int = 0
    decoded_blocks: int = 0
    peak_memory: int = 0
    operators: list[OperatorMetric] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_blocks": self.scanned_blocks,
            "pruned_blocks": self.pruned_blocks,
            "cache_hits": self.cache_hits,
            "bytes_read": self.bytes_read,
            "rows_examined": self.rows_examined,
            "rows_output": self.rows_output,
            "compressed_operator_blocks": self.compressed_operator_blocks,
            "decoded_blocks": self.decoded_blocks,
            "peak_memory": self.peak_memory,
            "operators": [o.to_dict() for o in self.operators],
        }


@dataclass(slots=True)
class ColumnExecMeta:
    name: str
    column_id: int
    file_path: str
    logical_type: str


@dataclass(slots=True)
class ExecutionContext:
    version_id: int
    columns: dict[str, ColumnExecMeta]
    pruning: dict[tuple[str, int], BlockPruningEntry]
    readers: dict[str, Any] = field(default_factory=dict)
    cache: BlockCache = field(default_factory=get_block_cache)
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    cancelled: bool = False
    active_block: tuple[str, int] | None = None

    def check_cancel(self) -> None:
        if self.cancelled:
            raise QueryCancelledError()

    def reader_for(self, column: str):
        if column not in self.readers:
            meta = self.columns[column]
            from app.engine.storage.reader import ColumnReader

            self.readers[column] = ColumnReader.open(Path(meta.file_path))
        return self.readers[column]

    def is_block_pruned(self, column: str, block_id: int) -> bool:
        entry = self.pruning.get((column, block_id))
        return entry is not None and entry.state == BlockPruneState.SKIPPED


class QueryCancelledError(Exception):
    pass
