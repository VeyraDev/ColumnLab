from __future__ import annotations

import time

from app.engine.execution.context import ExecutionContext, OperatorMetric
from app.engine.vectors import SelectionVector


def bitmap_and(
    ctx: ExecutionContext,
    left: SelectionVector,
    right: SelectionVector,
    *,
    operator_id: str,
) -> SelectionVector:
    ctx.check_cancel()
    start = time.perf_counter_ns()
    result = left.and_with(right)
    elapsed = time.perf_counter_ns() - start
    ctx.metrics.operators.append(
        OperatorMetric(
            operator_id=operator_id,
            operator_type="BitmapAnd",
            input_rows=left.length + right.length,
            output_rows=result.selected_count(),
            elapsed_ns=elapsed,
        )
    )
    return result


def bitmap_or(
    ctx: ExecutionContext,
    left: SelectionVector,
    right: SelectionVector,
    *,
    operator_id: str,
) -> SelectionVector:
    ctx.check_cancel()
    start = time.perf_counter_ns()
    result = left.or_with(right)
    elapsed = time.perf_counter_ns() - start
    ctx.metrics.operators.append(
        OperatorMetric(
            operator_id=operator_id,
            operator_type="BitmapOr",
            input_rows=left.length + right.length,
            output_rows=result.selected_count(),
            elapsed_ns=elapsed,
        )
    )
    return result
