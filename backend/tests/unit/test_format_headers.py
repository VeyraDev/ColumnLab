import struct

import pytest

from app.engine.format.constants import FILE_HEADER_SIZE, FOOTER_SIZE, FORMAT_VERSION
from app.engine.format.crc32 import crc32
from app.engine.format.errors import CrcMismatchError, InvalidMagicError, TruncatedFileError, UnsupportedVersionError
from app.engine.format.headers import BlockIndexEntry, FileFooter, FileHeader, pack_index, unpack_index
from app.engine.types import LogicalType


def test_file_header_roundtrip():
    header = FileHeader(logical_type=LogicalType.int64(), total_rows=100, block_count=3, footer_offset=999)
    packed = header.pack()
    assert len(packed) == FILE_HEADER_SIZE
    restored = FileHeader.unpack(packed)
    assert restored.total_rows == 100
    assert restored.block_count == 3
    assert restored.footer_offset == 999


def test_file_header_bad_magic():
    header = FileHeader(logical_type=LogicalType.int64()).pack()
    bad = b"BADMAGIC" + header[8:]
    with pytest.raises(InvalidMagicError):
        FileHeader.unpack(bad)


def test_file_header_bad_version():
    header = FileHeader(logical_type=LogicalType.int64()).pack()
    bad = header[:8] + struct.pack("<H", 99) + header[10:]
    with pytest.raises(UnsupportedVersionError):
        FileHeader.unpack(bad)


def test_file_header_crc_tamper():
    header = bytearray(FileHeader(logical_type=LogicalType.int64()).pack())
    header[20] ^= 0xFF
    with pytest.raises(CrcMismatchError):
        FileHeader.unpack(bytes(header))


def test_footer_roundtrip():
    footer = FileFooter(
        index_offset=100,
        index_length=96,
        index_crc32=123,
        column_raw_bytes=1000,
        column_encoded_bytes=400,
        column_stats_offset=500,
        column_stats_length=24,
    )
    packed = footer.pack()
    assert len(packed) == FOOTER_SIZE
    restored = FileFooter.unpack(packed, 0)
    assert restored.index_offset == 100
    assert restored.column_encoded_bytes == 400


def test_index_roundtrip():
    entries = [
        BlockIndexEntry(
            block_id=0,
            row_group_id=0,
            offset=64,
            total_block_length=200,
            row_start=0,
            row_count=512,
            encoding=__import__("app.engine.types", fromlist=["Encoding"]).Encoding.RLE,
            null_count=1,
            payload_crc32=0xAABBCCDD,
            stats_offset=64,
            stats_length=16,
        )
    ]
    data = pack_index(entries)
    restored = unpack_index(data)
    assert len(restored) == 1
    assert restored[0].row_count == 512


def test_truncated_header():
    with pytest.raises(TruncatedFileError):
        FileHeader.unpack(b"\x00" * 10)
