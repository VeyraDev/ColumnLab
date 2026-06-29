from __future__ import annotations

import math
import random
import statistics
from typing import Sequence


def summarize(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p95_idx = max(0, min(n - 1, math.ceil(n * 0.95) - 1))
    return {
        "count": float(n),
        "mean": statistics.mean(sorted_vals),
        "median": statistics.median(sorted_vals),
        "p95": sorted_vals[p95_idx],
        "stdev": statistics.pstdev(sorted_vals) if n > 1 else 0.0,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }


def summarize_by_metric(samples: list[tuple[str, float]]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[float]] = {}
    for name, value in samples:
        buckets.setdefault(name, []).append(value)
    return {name: summarize(vals) for name, vals in buckets.items()}
