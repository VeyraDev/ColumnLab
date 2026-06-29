from __future__ import annotations

import time
from typing import Any

from app.engine.cache.block_cache import CacheKey
from app.engine.codecs.base import EncodedBlock
from app.engine.execution.context import ExecutionContext, OperatorMetric
from app.engine.storage.reader import ColumnReader


def read_block(
    ctx: ExecutionContext,
    *,
    column: str,
    column_id: int,
    block_id: int,
    operator_id: str,
) -> EncodedBlock | None:
    if ctx.is_block_pruned(column, block_id):
        ctx.metrics.pruned_blocks += 1
        return None
    ctx.check_cancel()
    ctx.active_block = (column, block_id)
    key = CacheKey(
        version_id=ctx.version_id,
        column_id=column_id,
        block_id=block_id,
        representation="encoded",
    )
    cached = ctx.cache.get(key)
    if cached is not None:
        ctx.metrics.cache_hits += 1
        ctx.metrics.scanned_blocks += 1
        return cached
    reader: ColumnReader = ctx.reader_for(column)
    start = time.perf_counter_ns()
    block = reader.read_block(block_id)
    elapsed = time.perf_counter_ns() - start
    ctx.metrics.scanned_blocks += 1
    ctx.metrics.bytes_read += block.encoded_bytes
    ctx.cache.put(key, block, block.encoded_bytes)
    ctx.metrics.operators.append(
        OperatorMetric(
            operator_id=operator_id,
            operator_type="BlockScan",
            input_rows=0,
            output_rows=_block_row_count(block),
            elapsed_ns=elapsed,
        )
    )
    return block


def _block_row_count(block: EncodedBlock) -> int:
    from app.engine.vectors import NullBitmap

    nulls, _ = NullBitmap.deserialize(block.payload)
    return nulls.length
