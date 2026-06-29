from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from app.engine.codecs.base import EncodedBlock
from app.engine.codecs.selector import select_codec
from app.engine.format.constants import BLOCK_HEADER_SIZE
from app.engine.format.crc32 import crc32
from app.engine.format.headers import (
    BlockHeader,
    BlockIndexEntry,
    FileFooter,
    FileHeader,
    encode_stats,
    pack_index,
)
from app.engine.storage.row_group import RowGroupSlice
from app.engine.types import LogicalType
from app.engine.vectors import ValueVector, sort_key


@dataclass(slots=True)
class ColumnFileMeta:
    path: Path
    total_rows: int
    block_count: int
    column_raw_bytes: int
    column_encoded_bytes: int


@dataclass
class ColumnWriter:
    path: Path
    logical_type: LogicalType
    column_id: int = 0
    target_block_bytes: int = 65536
    schema_fingerprint: int = 0
    created_at_epoch: int = 0
    _tmp_path: Path = field(init=False)
    _file: BinaryIO | None = field(default=None, init=False)
    _index: list[BlockIndexEntry] = field(default_factory=list)
    _total_rows: int = 0
    _column_raw_bytes: int = 0
    _column_encoded_bytes: int = 0
    _column_min: Any = None
    _column_max: Any = None
    _next_block_id: int = 0

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self._tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        if self._tmp_path.exists():
            self._tmp_path.unlink()
        self._file = open(self._tmp_path, "w+b")
        header = FileHeader(
            logical_type=self.logical_type,
            column_id=self.column_id,
            target_block_bytes=self.target_block_bytes,
            schema_fingerprint=self.schema_fingerprint,
            created_at_epoch=self.created_at_epoch,
        )
        assert self._file is not None
        self._file.write(header.pack())

    def write_slice(self, slice_: RowGroupSlice, column_name: str) -> None:
        vector = slice_.columns[column_name]
        nulls = vector.null_bitmap()
        selection = select_codec(vector, nulls)
        self._write_block(
            block=selection.winner,
            block_id=self._next_block_id,
            row_group_id=slice_.row_group_id,
            row_start=slice_.row_start,
            row_count=slice_.row_count,
        )
        self._next_block_id += 1
        self._total_rows = max(self._total_rows, slice_.row_start + slice_.row_count)
        self._update_column_minmax(vector)

    def write_vector(self, vector: ValueVector, row_group_id: int, row_start: int) -> None:
        nulls = vector.null_bitmap()
        selection = select_codec(vector, nulls)
        self._write_block(
            block=selection.winner,
            block_id=self._next_block_id,
            row_group_id=row_group_id,
            row_start=row_start,
            row_count=vector.length,
        )
        self._next_block_id += 1
        self._total_rows = max(self._total_rows, row_start + vector.length)
        self._update_column_minmax(vector)

    def _update_column_minmax(self, vector: ValueVector) -> None:
        non_null = [v for v in vector.values if v is not None]
        if not non_null:
            return
        block_min = min(non_null, key=lambda v: sort_key(self.logical_type, v))
        block_max = max(non_null, key=lambda v: sort_key(self.logical_type, v))
        self._column_min = block_min if self._column_min is None else min(
            self._column_min, block_min, key=lambda v: sort_key(self.logical_type, v)
        )
        self._column_max = block_max if self._column_max is None else max(
            self._column_max, block_max, key=lambda v: sort_key(self.logical_type, v)
        )

    def _write_block(
        self,
        *,
        block: EncodedBlock,
        block_id: int,
        row_group_id: int,
        row_start: int,
        row_count: int,
    ) -> None:
        assert self._file is not None
        stats = encode_stats(self.logical_type, block.min_value, block.max_value)
        payload_crc = crc32(block.payload)
        run_or_dict = block.run_count or block.dictionary_count
        header = BlockHeader(
            encoding=block.encoding,
            block_id=block_id,
            row_group_id=row_group_id,
            row_start=row_start,
            row_count=row_count,
            null_count=block.null_count,
            distinct_count=block.distinct_count,
            raw_bytes=block.raw_bytes,
            encoded_bytes=block.encoded_bytes,
            stats_bytes=len(stats),
            payload_crc32=payload_crc,
            run_count_or_dict_count=run_or_dict,
        )
        offset = self._file.tell()
        header_bytes = header.pack()
        self._file.write(header_bytes)
        self._file.write(stats)
        self._file.write(block.payload)
        total_len = len(header_bytes) + len(stats) + len(block.payload)
        self._index.append(
            BlockIndexEntry(
                block_id=block_id,
                row_group_id=row_group_id,
                offset=offset,
                total_block_length=total_len,
                row_start=row_start,
                row_count=row_count,
                encoding=block.encoding,
                null_count=block.null_count,
                payload_crc32=payload_crc,
                stats_offset=BLOCK_HEADER_SIZE,
                stats_length=len(stats),
            )
        )
        self._column_raw_bytes += block.raw_bytes
        self._column_encoded_bytes += block.encoded_bytes

    def finalize(self) -> ColumnFileMeta:
        assert self._file is not None
        index_bytes = pack_index(self._index)
        index_offset = self._file.tell()
        self._file.write(index_bytes)
        column_stats = encode_stats(self.logical_type, self._column_min, self._column_max)
        column_stats_offset = self._file.tell()
        self._file.write(column_stats)
        footer = FileFooter(
            index_offset=index_offset,
            index_length=len(index_bytes),
            index_crc32=crc32(index_bytes),
            column_raw_bytes=self._column_raw_bytes,
            column_encoded_bytes=self._column_encoded_bytes,
            column_stats_offset=column_stats_offset,
            column_stats_length=len(column_stats),
        )
        footer_offset = self._file.tell()
        self._file.write(footer.pack())
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()
        self._file = None

        header = FileHeader(
            logical_type=self.logical_type,
            column_id=self.column_id,
            total_rows=self._total_rows,
            block_count=len(self._index),
            target_block_bytes=self.target_block_bytes,
            footer_offset=footer_offset,
            schema_fingerprint=self.schema_fingerprint,
            created_at_epoch=self.created_at_epoch,
        )
        with open(self._tmp_path, "r+b") as fh:
            fh.seek(0)
            fh.write(header.pack())
            fh.flush()
            os.fsync(fh.fileno())

        if self.path.exists():
            self.path.unlink()
        os.replace(self._tmp_path, self.path)
        return ColumnFileMeta(
            path=self.path,
            total_rows=self._total_rows,
            block_count=len(self._index),
            column_raw_bytes=self._column_raw_bytes,
            column_encoded_bytes=self._column_encoded_bytes,
        )

    def abort(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
        if self._tmp_path.exists():
            self._tmp_path.unlink()
