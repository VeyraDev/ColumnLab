from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Any

from app.engine.format.constants import (
    BLOCK_HEADER_SIZE,
    BLOCK_MAGIC,
    FILE_HEADER_SIZE,
    FILE_MAGIC,
    FLAG_NULLABLE,
    FOOTER_MAGIC,
    FOOTER_SIZE,
    FORMAT_VERSION,
    INDEX_ENTRY_SIZE,
)
from app.engine.format.crc32 import crc32, verify_crc32
from app.engine.format.errors import InvalidMagicError, TruncatedFileError, UnsupportedVersionError
from app.engine.types import Encoding, LogicalType, LogicalTypeId
from app.engine.vectors import serialize_typed_value


@dataclass(slots=True)
class FileHeader:
    logical_type: LogicalType
    column_id: int = 0
    total_rows: int = 0
    block_count: int = 0
    target_block_bytes: int = 65536
    footer_offset: int = 0
    schema_fingerprint: int = 0
    created_at_epoch: int = 0
    flags: int = FLAG_NULLABLE

    def pack(self) -> bytes:
        created = self.created_at_epoch or int(time.time())
        body = struct.pack(
            "<8sHHBBHQQIIQQI",
            FILE_MAGIC,
            FORMAT_VERSION,
            FILE_HEADER_SIZE,
            int(self.logical_type.type_id),
            self.flags,
            self.logical_type.scale & 0xFFFF,
            self.column_id,
            self.total_rows,
            self.block_count,
            self.target_block_bytes,
            self.footer_offset,
            self.schema_fingerprint,
            created & 0xFFFFFFFF,
        )
        checksum = crc32(body)
        return body + struct.pack("<I", checksum)

    @classmethod
    def unpack(cls, data: bytes) -> FileHeader:
        if len(data) < FILE_HEADER_SIZE:
            raise TruncatedFileError("file header truncated")
        if data[:8] != FILE_MAGIC:
            raise InvalidMagicError(f"invalid file magic: {data[:8]!r}")
        (
            _magic,
            version,
            header_size,
            type_id,
            flags,
            scale,
            column_id,
            total_rows,
            block_count,
            target_block_bytes,
            footer_offset,
            schema_fingerprint,
            created_at_epoch,
        ) = struct.unpack("<8sHHBBHQQIIQQI", data[:60])
        if version != FORMAT_VERSION:
            raise UnsupportedVersionError(f"unsupported format version {version}")
        stored_crc, = struct.unpack("<I", data[60:64])
        verify_crc32(data[:60], stored_crc)
        if header_size != FILE_HEADER_SIZE:
            raise UnsupportedVersionError(f"unexpected header size {header_size}")
        return cls(
            logical_type=LogicalType(LogicalTypeId(type_id), scale=scale),
            column_id=column_id,
            total_rows=total_rows,
            block_count=block_count,
            target_block_bytes=target_block_bytes,
            footer_offset=footer_offset,
            schema_fingerprint=schema_fingerprint,
            created_at_epoch=created_at_epoch,
            flags=flags,
        )


@dataclass(slots=True)
class BlockHeader:
    encoding: Encoding
    block_id: int
    row_group_id: int
    row_start: int
    row_count: int
    null_count: int
    distinct_count: int
    raw_bytes: int
    encoded_bytes: int
    stats_bytes: int
    payload_crc32: int
    run_count_or_dict_count: int = 0

    def pack(self) -> bytes:
        return struct.pack(
            "<4sHBBIIQIIIIIIIIII",
            BLOCK_MAGIC,
            BLOCK_HEADER_SIZE,
            int(self.encoding),
            0,
            self.block_id,
            self.row_group_id,
            self.row_start,
            self.row_count,
            self.null_count,
            self.distinct_count,
            self.raw_bytes & 0xFFFFFFFF,
            self.encoded_bytes & 0xFFFFFFFF,
            self.stats_bytes,
            self.payload_crc32,
            self.run_count_or_dict_count,
            0,
            0,
        )

    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> tuple[BlockHeader, int]:
        if len(data) < offset + BLOCK_HEADER_SIZE:
            raise TruncatedFileError("block header truncated")
        chunk = data[offset : offset + BLOCK_HEADER_SIZE]
        if chunk[:4] != BLOCK_MAGIC:
            raise InvalidMagicError(f"invalid block magic: {chunk[:4]!r}")
        (
            _magic,
            header_size,
            encoding,
            _flags,
            block_id,
            row_group_id,
            row_start,
            row_count,
            null_count,
            distinct_count,
            raw_bytes,
            encoded_bytes,
            stats_bytes,
            payload_crc32,
            run_count_or_dict_count,
            _reserved,
            _padding,
        ) = struct.unpack("<4sHBBIIQIIIIIIIIII", chunk)
        if header_size != BLOCK_HEADER_SIZE:
            raise UnsupportedVersionError(f"unexpected block header size {header_size}")
        return (
            cls(
                encoding=Encoding(encoding),
                block_id=block_id,
                row_group_id=row_group_id,
                row_start=row_start,
                row_count=row_count,
                null_count=null_count,
                distinct_count=distinct_count,
                raw_bytes=raw_bytes,
                encoded_bytes=encoded_bytes,
                stats_bytes=stats_bytes,
                payload_crc32=payload_crc32,
                run_count_or_dict_count=run_count_or_dict_count,
            ),
            offset + BLOCK_HEADER_SIZE,
        )


@dataclass(slots=True)
class BlockIndexEntry:
    block_id: int
    row_group_id: int
    offset: int
    total_block_length: int
    row_start: int
    row_count: int
    encoding: Encoding
    null_count: int
    payload_crc32: int
    stats_offset: int
    stats_length: int

    def pack(self) -> bytes:
        tail = struct.pack("<IIII", self.stats_offset, self.stats_length, 0, 0) + b"\x00" * 4
        return struct.pack(
            "<IIQIQIIII",
            self.block_id,
            self.row_group_id,
            self.offset,
            self.total_block_length,
            self.row_start,
            self.row_count,
            int(self.encoding),
            self.null_count,
            self.payload_crc32,
        ) + tail

    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> tuple[BlockIndexEntry, int]:
        if len(data) < offset + INDEX_ENTRY_SIZE:
            raise TruncatedFileError("index entry truncated")
        fields = struct.unpack("<IIQIQIIII", data[offset : offset + 44])
        stats_offset, stats_length, _, _ = struct.unpack("<IIII", data[offset + 44 : offset + 60])
        return (
            cls(
                block_id=fields[0],
                row_group_id=fields[1],
                offset=fields[2],
                total_block_length=fields[3],
                row_start=fields[4],
                row_count=fields[5],
                encoding=Encoding(fields[6]),
                null_count=fields[7],
                payload_crc32=fields[8],
                stats_offset=stats_offset,
                stats_length=stats_length,
            ),
            offset + INDEX_ENTRY_SIZE,
        )


@dataclass(slots=True)
class FileFooter:
    index_offset: int
    index_length: int
    index_crc32: int
    column_raw_bytes: int
    column_encoded_bytes: int
    column_stats_offset: int
    column_stats_length: int

    def pack(self) -> bytes:
        body = struct.pack(
            "<8sQIIQQQII",
            FOOTER_MAGIC,
            self.index_offset,
            self.index_length,
            self.index_crc32,
            self.column_raw_bytes,
            self.column_encoded_bytes,
            self.column_stats_offset,
            self.column_stats_length,
            0,
        )
        checksum = crc32(body)
        return body + struct.pack("<II", checksum, FOOTER_SIZE)

    @classmethod
    def unpack(cls, data: bytes, offset: int) -> FileFooter:
        if len(data) < offset + FOOTER_SIZE:
            raise TruncatedFileError("footer truncated")
        chunk = data[offset : offset + FOOTER_SIZE]
        if chunk[:8] != FOOTER_MAGIC:
            raise InvalidMagicError(f"invalid footer magic: {chunk[:8]!r}")
        (
            index_offset,
            index_length,
            index_crc32,
            column_raw,
            column_encoded,
            column_stats_offset,
            column_stats_length,
            _reserved,
        ) = struct.unpack("<QIIQQQII", chunk[8:56])
        stored_crc, = struct.unpack("<I", chunk[56:60])
        verify_crc32(chunk[:56], stored_crc)
        footer_size, = struct.unpack("<I", chunk[60:64])
        if footer_size != FOOTER_SIZE:
            raise UnsupportedVersionError(f"unexpected footer size {footer_size}")
        return cls(
            index_offset=index_offset,
            index_length=index_length,
            index_crc32=index_crc32,
            column_raw_bytes=column_raw,
            column_encoded_bytes=column_encoded,
            column_stats_offset=column_stats_offset,
            column_stats_length=column_stats_length,
        )


def pack_index(entries: list[BlockIndexEntry]) -> bytes:
    return b"".join(entry.pack() for entry in entries)


def unpack_index(data: bytes) -> list[BlockIndexEntry]:
    entries: list[BlockIndexEntry] = []
    offset = 0
    while offset < len(data):
        entry, offset = BlockIndexEntry.unpack(data, offset)
        entries.append(entry)
    return entries


def encode_stats(logical_type: LogicalType, min_value: Any, max_value: Any) -> bytes:
    min_blob = b"" if min_value is None else serialize_typed_value(logical_type, min_value)
    max_blob = b"" if max_value is None else serialize_typed_value(logical_type, max_value)
    return struct.pack("<II", len(min_blob), len(max_blob)) + min_blob + max_blob


def decode_stats(logical_type: LogicalType, data: bytes) -> tuple[Any, Any]:
    if not data:
        return None, None
    min_len, max_len = struct.unpack("<II", data[:8])
    pos = 8
    min_blob = data[pos : pos + min_len]
    pos += min_len
    max_blob = data[pos : pos + max_len]
    from app.engine.vectors import deserialize_typed_value

    min_value = None if not min_blob else deserialize_typed_value(logical_type, min_blob, 0)[0]
    max_value = None if not max_blob else deserialize_typed_value(logical_type, max_blob, 0)[0]
    return min_value, max_value
