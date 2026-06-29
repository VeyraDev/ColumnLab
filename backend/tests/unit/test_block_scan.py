from pathlib import Path

from app.engine.cache.block_cache import BlockCache
from app.engine.execution.block_scan import read_block
from app.engine.execution.context import ColumnExecMeta, ExecutionContext
from app.engine.query.pruning import BlockPruneState, BlockPruningEntry, BlockVerdict
from app.engine.storage.reader import ColumnReader
from app.engine.storage.row_group import build_slices_from_columns
from app.engine.storage.writer import ColumnWriter
from app.engine.types import LogicalType


def _write_column(path: Path, values: list[int]) -> None:
    slices = build_slices_from_columns({"v": values}, min_rows=20, max_rows=200, target_block_bytes=512)
    writer = ColumnWriter(path, LogicalType.int64())
    for s in slices:
        writer.write_slice(s, "v")
    writer.finalize()


def test_block_cache_lru_eviction():
    cache = BlockCache(max_bytes=100)
    from app.engine.cache.block_cache import CacheKey

    key1 = CacheKey(version_id=1, column_id=1, block_id=0, representation="encoded")
    key2 = CacheKey(version_id=1, column_id=1, block_id=1, representation="encoded")
    cache.put(key1, "a", 60)
    cache.put(key2, "b", 60)
    assert cache.get(key1) is None
    assert cache.get(key2) == "b"
    assert cache.stats.evictions >= 1


def test_read_block_skips_pruned(tmp_path: Path):
    col_file = tmp_path / "id.col"
    _write_column(col_file, list(range(100)))
    ctx = ExecutionContext(
        version_id=1,
        columns={
            "id": ColumnExecMeta(name="id", column_id=1, file_path=str(col_file), logical_type="INT64")
        },
        pruning={
            ("id", 0): BlockPruningEntry(
                column="id",
                block_id=0,
                state=BlockPruneState.SKIPPED,
                verdict=BlockVerdict.ALWAYS_FALSE,
                reason="test",
            )
        },
    )
    result = read_block(ctx, column="id", column_id=1, block_id=0, operator_id="scan")
    assert result is None
    assert ctx.metrics.pruned_blocks == 1


def test_read_block_cache_hit(tmp_path: Path):
    col_file = tmp_path / "id.col"
    _write_column(col_file, list(range(100)))
    cache = BlockCache(max_bytes=1024 * 1024)
    ctx = ExecutionContext(
        version_id=1,
        columns={
            "id": ColumnExecMeta(name="id", column_id=1, file_path=str(col_file), logical_type="INT64")
        },
        pruning={},
        cache=cache,
    )
    b1 = read_block(ctx, column="id", column_id=1, block_id=0, operator_id="scan1")
    b2 = read_block(ctx, column="id", column_id=1, block_id=0, operator_id="scan2")
    assert b1 is not None and b2 is not None
    assert ctx.metrics.cache_hits >= 1
