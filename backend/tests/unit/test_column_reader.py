from pathlib import Path

import pytest

from app.engine.format.constants import FILE_MAGIC
from app.engine.format.errors import CrcMismatchError, InvalidMagicError, TruncatedFileError, UnsupportedVersionError
from app.engine.storage.reader import ColumnReader
from app.engine.storage.row_group import build_slices_from_columns
from app.engine.storage.writer import ColumnWriter
from app.engine.types import LogicalType


def _write_sample(path: Path, values: list[int]) -> None:
    slices = build_slices_from_columns({"v": values}, min_rows=20, max_rows=200, target_block_bytes=512)
    writer = ColumnWriter(path, LogicalType.int64())
    for s in slices:
        writer.write_slice(s, "v")
    writer.finalize()


def test_reader_index_only(tmp_path: Path):
    path = tmp_path / "sample.col"
    _write_sample(path, list(range(150)))
    index = ColumnReader.load_index_only(path)
    assert len(index) >= 1
    assert index[0].row_count > 0


def test_reader_random_block_roundtrip(tmp_path: Path):
    path = tmp_path / "sample.col"
    values = list(range(500))
    _write_sample(path, values)
    reader = ColumnReader.open(path)
    mid = len(reader.index) // 2
    vec = reader.decode_block(mid)
    assert vec.length == reader.index[mid].row_count


def test_reader_payload_crc_tamper(tmp_path: Path):
    path = tmp_path / "tamper.col"
    _write_sample(path, list(range(80)))
    data = bytearray(path.read_bytes())
    data[200] ^= 0xFF
    path.write_bytes(data)
    reader = ColumnReader.open(path)
    with pytest.raises(CrcMismatchError):
        reader.read_block(0)


def test_reader_truncated_file(tmp_path: Path):
    path = tmp_path / "trunc.col"
    _write_sample(path, list(range(50)))
    path.write_bytes(path.read_bytes()[:100])
    with pytest.raises(TruncatedFileError):
        ColumnReader.open(path)


def test_reader_bad_magic(tmp_path: Path):
    path = tmp_path / "bad.col"
    _write_sample(path, list(range(50)))
    data = bytearray(path.read_bytes())
    data[:4] = b"BAD!"
    path.write_bytes(data)
    with pytest.raises(InvalidMagicError):
        ColumnReader.open(path)


def test_reader_bad_version(tmp_path: Path):
    path = tmp_path / "ver.col"
    _write_sample(path, list(range(50)))
    data = bytearray(path.read_bytes())
    data[9] = 99
    path.write_bytes(data)
    with pytest.raises(UnsupportedVersionError):
        ColumnReader.open(path)
