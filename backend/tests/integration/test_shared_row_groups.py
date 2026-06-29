from __future__ import annotations

from pathlib import Path

from app.engine.storage.reader import ColumnReader
from app.engine.storage.row_group import build_slices_from_columns
from app.engine.storage.writer import ColumnWriter
from app.engine.types import LogicalType


def test_shared_row_groups_row_boundaries_match(tmp_path: Path) -> None:
    columns = {
        "a": list(range(600)),
        "b": [f"item-{i % 7}" for i in range(600)],
        "c": [i * 2 for i in range(600)],
    }
    slices = build_slices_from_columns(
        columns,
        min_rows=50,
        max_rows=200,
        target_block_bytes=1024,
    )
    paths: dict[str, Path] = {}
    readers: dict[str, ColumnReader] = {}
    for name, logical_type in (
        ("a", LogicalType.int64()),
        ("b", LogicalType.utf8()),
        ("c", LogicalType.int64()),
    ):
        path = tmp_path / f"{name}.col"
        writer = ColumnWriter(path, logical_type, target_block_bytes=1024, created_at_epoch=1_700_000_000)
        for slice_ in slices:
            writer.write_slice(slice_, name)
        writer.finalize()
        paths[name] = path
        readers[name] = ColumnReader.open(path)

    ref = readers["a"].index
    for name in ("b", "c"):
        index = readers[name].index
        assert len(index) == len(ref)
        for left, right in zip(ref, index, strict=True):
            assert left.row_start == right.row_start
            assert left.row_count == right.row_count
            assert left.row_group_id == right.row_group_id


def test_shared_row_groups_end_to_end_decode(tmp_path: Path) -> None:
    columns = {
        "a": list(range(400)),
        "b": [f"tag-{i % 5}" for i in range(400)],
        "c": [1000 + i for i in range(400)],
    }
    slices = build_slices_from_columns(
        columns,
        min_rows=40,
        max_rows=150,
        target_block_bytes=768,
    )
    for name, logical_type in (
        ("a", LogicalType.int64()),
        ("b", LogicalType.utf8()),
        ("c", LogicalType.int64()),
    ):
        path = tmp_path / f"{name}.col"
        writer = ColumnWriter(path, logical_type, created_at_epoch=1_700_000_000)
        for slice_ in slices:
            writer.write_slice(slice_, name)
        writer.finalize()
        reader = ColumnReader.open(path)
        decoded: list = []
        for entry in reader.index:
            decoded.extend(reader.decode_block(entry.block_id).values)
        assert decoded == columns[name]
