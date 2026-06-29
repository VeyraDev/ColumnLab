import pickle
from pathlib import Path

import pytest

from app.engine.format.constants import FILE_MAGIC
from app.engine.storage.reader import ColumnReader
from app.engine.storage.row_group import build_slices_from_columns
from app.engine.storage.writer import ColumnWriter
from app.engine.types import LogicalType


def test_column_writer_not_json_or_pickle(tmp_path: Path):
    path = tmp_path / "col.col"
    columns = {"v": list(range(100))}
    slices = build_slices_from_columns(columns, min_rows=10, max_rows=100, target_block_bytes=512)
    writer = ColumnWriter(path, LogicalType.int64(), target_block_bytes=512)
    for s in slices:
        writer.write_slice(s, "v")
    meta = writer.finalize()
    data = path.read_bytes()
    assert data.startswith(FILE_MAGIC)
    assert not data.startswith(b"{")
    assert not data.startswith(b"[")
    assert not data.startswith(pickle.dumps([1])[:1])
    assert meta.block_count >= 1
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_column_writer_abort_no_final(tmp_path: Path):
    path = tmp_path / "abort.col"
    writer = ColumnWriter(path, LogicalType.int64())
    writer.abort()
    assert not path.exists()


def test_writer_reader_roundtrip(tmp_path: Path):
    path = tmp_path / "roundtrip.col"
    original = list(range(300))
    slices = build_slices_from_columns({"v": original}, min_rows=50, max_rows=200, target_block_bytes=1024)
    writer = ColumnWriter(path, LogicalType.int64())
    for s in slices:
        writer.write_slice(s, "v")
    writer.finalize()
    reader = ColumnReader.open(path)
    index_only = ColumnReader.load_index_only(path)
    assert len(index_only) == len(reader.index)
    decoded: list = []
    for entry in reader.index:
        vec = reader.decode_block(entry.block_id)
        decoded.extend(vec.values)
    assert decoded == original
