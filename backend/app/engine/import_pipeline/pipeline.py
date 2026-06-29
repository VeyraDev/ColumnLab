from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.engine.import_pipeline.csv_parser import iter_csv_rows
from app.engine.import_pipeline.normalizer import NormalizationError, Normalizer
from app.engine.import_pipeline.type_infer import InferredColumn, infer_from_samples, parse_logical_type
from app.engine.import_pipeline.verifier import verify_column_files
from app.engine.import_pipeline.xlsx_parser import iter_xlsx_rows
from app.engine.storage.reader import ColumnReader
from app.engine.storage.row_group import RowGroupBuilder, RowGroupSlice
from app.engine.storage.writer import ColumnWriter
from app.engine.types import Encoding, LogicalType


ProgressCallback = Callable[[str, int, int, str, int], None]
CancelCallback = Callable[[], bool]


@dataclass(slots=True)
class ColumnWriteResult:
    name: str
    logical_type: LogicalType
    path: Path
    block_count: int
    raw_bytes: int
    encoded_bytes: int
    blocks: list[dict]


@dataclass(slots=True)
class PipelineResult:
    row_count: int
    row_group_count: int
    columns: list[ColumnWriteResult]
    error_count: int
    error_samples: list[dict]
    schema: list[InferredColumn]


@dataclass
class ImportPipeline:
    source_path: Path
    output_dir: Path
    import_mode: str = "strict"
    target_block_bytes: int = 65536
    schema_overrides: list[dict] | None = None
    on_progress: ProgressCallback | None = None
    should_cancel: CancelCallback | None = None
    _columns: list[InferredColumn] = field(default_factory=list, init=False)
    _normalizers: dict[str, Normalizer] = field(default_factory=dict, init=False)
    _writers: dict[str, ColumnWriter] = field(default_factory=dict, init=False)
    _row_group_count: int = 0

    def run(self) -> PipelineResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        header = self._read_header()
        sample_rows = self._sample_rows(header)
        self._emit("inferring", 0, 0, "", 0)
        self._columns = self._apply_overrides(infer_from_samples(header, sample_rows))
        self._normalizers = {
            col.name: Normalizer(col.logical_type, col.name, mode=self.import_mode)
            for col in self._columns
        }
        schemas = {col.name: col.logical_type for col in self._columns}
        builder = RowGroupBuilder(
            schemas=schemas,
            target_block_bytes=self.target_block_bytes,
            min_rows=min(512, max(1, self.target_block_bytes // 128)),
            max_rows=65536,
        )
        for col in self._columns:
            self._writers[col.name] = ColumnWriter(
                self.output_dir / f"{col.name}.col",
                col.logical_type,
                target_block_bytes=self.target_block_bytes,
            )

        row_number = 0
        bytes_read = 0
        self._emit("partitioning", 0, 0, "", self._error_count())
        for cells in self._iter_data_rows():
            if self._check_cancel():
                raise RuntimeError("cancelled")
            row_number += 1
            row_dict: dict[str, Any] = {}
            for col_idx, col in enumerate(self._columns):
                raw = cells[col_idx] if col_idx < len(cells) else ""
                bytes_read += len(str(raw).encode("utf-8"))
                norm = self._normalizers[col.name]
                prev_errors = norm.error_count
                row_dict[col.name] = norm.normalize(raw, row_number=row_number)
                if self.import_mode == "strict" and norm.error_count > prev_errors:
                    sample = norm.error_samples[-1]
                    raise NormalizationError(
                        sample["row"], sample["column"], sample["value"], sample["reason"]
                    )
            flushed = builder.append_row(row_dict)
            for slice_ in flushed:
                self._write_slice(slice_)
            if row_number % 256 == 0:
                self._emit("encoding", row_number, bytes_read, "", self._error_count())

        for slice_ in builder.finish():
            self._write_slice(slice_)

        column_results: list[ColumnWriteResult] = []
        for col in self._columns:
            self._emit("writing", row_number, bytes_read, col.name, self._error_count())
            meta = self._writers[col.name].finalize()
            reader = ColumnReader.open(self._writers[col.name].path)
            blocks = []
            for entry in reader.index:
                block = reader.read_block(entry.block_id)
                blocks.append(
                    {
                        "block_id": entry.block_id,
                        "row_start": entry.row_start,
                        "row_count": entry.row_count,
                        "encoding": entry.encoding.name,
                        "raw_bytes": block.raw_bytes,
                        "encoded_bytes": block.encoded_bytes,
                        "null_count": entry.null_count,
                        "payload_crc32": f"{entry.payload_crc32:08x}",
                        "total_block_length": entry.total_block_length,
                        "run_count": block.run_count if block.encoding == Encoding.RLE else 0,
                        "dictionary_count": block.dictionary_count
                        if block.encoding == Encoding.DICTIONARY
                        else 0,
                        "min_repr": str(block.min_value) if block.min_value is not None else None,
                        "max_repr": str(block.max_value) if block.max_value is not None else None,
                    }
                )
            column_results.append(
                ColumnWriteResult(
                    name=col.name,
                    logical_type=col.logical_type,
                    path=self._writers[col.name].path,
                    block_count=meta.block_count,
                    raw_bytes=meta.column_raw_bytes,
                    encoded_bytes=meta.column_encoded_bytes,
                    blocks=blocks,
                )
            )

        self._emit("validating", row_number, bytes_read, "", self._error_count())
        verify_column_files(
            {c.name: c.path for c in column_results},
            {c.name: c.logical_type for c in column_results},
        )
        return PipelineResult(
            row_count=row_number,
            row_group_count=self._row_group_count,
            columns=column_results,
            error_count=self._error_count(),
            error_samples=self._error_samples(),
            schema=self._columns,
        )

    def _read_header(self) -> list[str]:
        self._emit("parsing", 0, 0, "", 0)
        suffix = self.source_path.suffix.lower()
        if suffix == ".csv":
            for row in iter_csv_rows(self.source_path):
                return [c.strip() for c in row]
        if suffix == ".xlsx":
            for row in iter_xlsx_rows(self.source_path):
                return [c.strip() for c in row]
        raise ValueError(f"unsupported file type: {suffix}")
        return []

    def _sample_rows(self, header: list[str]) -> list[list[str]]:
        rows: list[list[str]] = []
        for cells in self._iter_data_rows():
            rows.append(cells)
            if len(rows) >= 500:
                break
        return rows

    def _iter_data_rows(self):
        suffix = self.source_path.suffix.lower()
        if suffix == ".csv":
            gen = iter_csv_rows(self.source_path)
        elif suffix == ".xlsx":
            gen = iter_xlsx_rows(self.source_path)
        else:
            raise ValueError(f"unsupported file type: {suffix}")
        next(gen)
        yield from gen

    def _apply_overrides(self, inferred: list[InferredColumn]) -> list[InferredColumn]:
        if not self.schema_overrides:
            return inferred
        override_map = {item["name"]: item for item in self.schema_overrides}
        result: list[InferredColumn] = []
        for col in inferred:
            ov = override_map.get(col.name)
            if ov:
                result.append(
                    InferredColumn(
                        name=col.name,
                        logical_type=parse_logical_type(ov["logical_type"], ov.get("scale", 0)),
                        nullable=ov.get("nullable", True),
                    )
                )
            else:
                result.append(col)
        return result

    def _write_slice(self, slice_: RowGroupSlice) -> None:
        self._row_group_count = max(self._row_group_count, slice_.row_group_id + 1)
        for name, writer in self._writers.items():
            writer.write_slice(slice_, name)

    def _error_count(self) -> int:
        return sum(n.error_count for n in self._normalizers.values())

    def _error_samples(self) -> list[dict]:
        samples: list[dict] = []
        for norm in self._normalizers.values():
            samples.extend(norm.error_samples)
        return samples[:20]

    def _emit(self, stage: str, rows: int, bytes_: int, column: str, errors: int) -> None:
        if self.on_progress:
            self.on_progress(stage, rows, bytes_, column, errors)

    def _check_cancel(self) -> bool:
        return bool(self.should_cancel and self.should_cancel())
