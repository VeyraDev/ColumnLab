from __future__ import annotations

import time
from typing import Any, Callable


def scan_rows_eq(rows: list[tuple[Any, ...]], column_index: int, target: Any) -> int:
    count = 0
    for row in rows:
        if row[column_index] == target:
            count += 1
    return count


def scan_rows_range(
    rows: list[tuple[Any, ...]],
    column_index: int,
    lower: Any,
    upper: Any,
) -> int:
    count = 0
    for row in rows:
        val = row[column_index]
        if val is None:
            continue
        if lower <= val <= upper:
            count += 1
    return count


def scan_rows_sum(rows: list[tuple[Any, ...]], column_index: int) -> int | float:
    total = 0
    for row in rows:
        val = row[column_index]
        if val is not None:
            total += val
    return total


def benchmark_row_baseline(
    rows: list[tuple[Any, ...]],
    *,
    eq_target: Any,
    range_bounds: tuple[Any, Any],
) -> dict[str, float]:
    col = 0
    start = time.perf_counter_ns()
    scan_rows_eq(rows, col, eq_target)
    eq_ns = time.perf_counter_ns() - start

    start = time.perf_counter_ns()
    scan_rows_range(rows, col, range_bounds[0], range_bounds[1])
    range_ns = time.perf_counter_ns() - start

    start = time.perf_counter_ns()
    scan_rows_sum(rows, col)
    sum_ns = time.perf_counter_ns() - start

    return {
        "row_filter_eq_ns": float(eq_ns),
        "row_filter_range_ns": float(range_ns),
        "row_aggregate_sum_ns": float(sum_ns),
    }


def rows_from_columns(columns: dict[str, list[Any]]) -> list[tuple[Any, ...]]:
    names = list(columns.keys())
    length = len(columns[names[0]])
    return [tuple(columns[name][i] for name in names) for i in range(length)]
