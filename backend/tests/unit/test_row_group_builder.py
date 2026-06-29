from app.engine.storage.row_group import RowGroupBuilder, build_slices_from_columns
from app.engine.types import LogicalType


def test_row_group_single_slice_small():
    builder = RowGroupBuilder(
        schemas={"a": LogicalType.int64(), "b": LogicalType.utf8()},
        target_block_bytes=65536,
        min_rows=1,
        max_rows=10000,
    )
    flushed = []
    for i in range(10):
        flushed.extend(builder.append_row({"a": i, "b": f"v{i}"}))
    flushed.extend(builder.finish())
    assert len(flushed) == 1
    assert flushed[0].row_count == 10
    assert flushed[0].row_start == 0
    assert set(flushed[0].columns.keys()) == {"a", "b"}


def test_row_group_multiple_slices():
    columns = {
        "id": list(range(2000)),
        "name": [f"n{i}" for i in range(2000)],
    }
    slices = build_slices_from_columns(columns, target_block_bytes=2048, min_rows=100, max_rows=1000)
    assert len(slices) >= 2
    for s in slices:
        assert s.row_count > 0
    # shared boundaries
    for i in range(len(slices)):
        assert slices[i].columns["id"].length == slices[i].columns["name"].length


def test_shared_row_start_count():
    columns = {
        "x": [1] * 600,
        "y": [2] * 600,
        "z": [3] * 600,
    }
    slices = build_slices_from_columns(columns, target_block_bytes=1024, min_rows=50, max_rows=500)
    for s in slices:
        assert s.columns["x"].length == s.columns["y"].length == s.columns["z"].length
        assert s.columns["x"].length == s.row_count
