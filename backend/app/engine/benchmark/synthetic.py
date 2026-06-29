from __future__ import annotations

import random
from typing import Any

from app.engine.benchmark.config import DistributionKind
from app.engine.types import LogicalType


def generate_int_column(
    distribution: DistributionKind,
    row_count: int,
    *,
    seed: int,
) -> list[int | None]:
    rng = random.Random(seed)
    if distribution == "run_length":
        values: list[int | None] = []
        while len(values) < row_count:
            run = rng.randint(8, 128)
            val = rng.randint(0, 5)
            values.extend([val] * min(run, row_count - len(values)))
        return values
    if distribution == "low_cardinality":
        return [rng.randint(0, 7) for _ in range(row_count)]
    if distribution == "high_cardinality":
        return [rng.randint(0, row_count * 2) for _ in range(row_count)]
    if distribution == "uniform":
        return [rng.randint(0, 1000) for _ in range(row_count)]
    if distribution == "skewed":
        choices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        weights = [50, 20, 10, 5, 4, 3, 3, 2, 2, 1]
        return [rng.choices(choices, weights=weights, k=1)[0] for _ in range(row_count)]
    if distribution == "with_null":
        return [None if rng.random() < 0.12 else rng.randint(0, 100) for _ in range(row_count)]
    if distribution == "mixed_business":
        statuses = [0, 1, 2]
        return [rng.choice(statuses) if rng.random() > 0.05 else None for _ in range(row_count)]
    raise ValueError(f"unknown distribution: {distribution}")


def generate_utf8_column(
    distribution: DistributionKind,
    row_count: int,
    *,
    seed: int,
) -> list[str | None]:
    rng = random.Random(seed + 1)
    if distribution in ("run_length", "low_cardinality", "mixed_business"):
        regions = ["north", "south", "east", "west", "central"]
        values: list[str | None] = []
        if distribution == "run_length":
            while len(values) < row_count:
                run = rng.randint(16, 96)
                val = rng.choice(regions)
                values.extend([val] * min(run, row_count - len(values)))
            return values
        return [rng.choice(regions) if rng.random() > 0.08 else None for _ in range(row_count)]
    if distribution == "high_cardinality":
        return [f"item-{rng.randint(0, row_count * 4)}" for _ in range(row_count)]
    if distribution == "with_null":
        return [None if rng.random() < 0.1 else f"tag-{rng.randint(0, 50)}" for _ in range(row_count)]
    return [f"val-{rng.randint(0, 500)}" for _ in range(row_count)]


def generate_dataset(
    distribution: DistributionKind,
    row_count: int,
    *,
    seed: int,
) -> dict[str, Any]:
    int_values = generate_int_column(distribution, row_count, seed=seed)
    str_values = generate_utf8_column(distribution, row_count, seed=seed)
    return {
        "distribution": distribution,
        "row_count": row_count,
        "seed": seed,
        "qty": int_values,
        "region": str_values,
        "logical_types": {
            "qty": LogicalType.int64(),
            "region": LogicalType.utf8(),
        },
    }
