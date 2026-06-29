from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

DistributionKind = Literal[
    "run_length",
    "low_cardinality",
    "high_cardinality",
    "uniform",
    "skewed",
    "with_null",
    "mixed_business",
]


@dataclass
class BenchmarkConfig:
    kind: Literal["codec", "query"] = "codec"
    seed: int = 42
    warmup_runs: int = 1
    repeat_runs: int = 3
    distribution: DistributionKind = "run_length"
    row_count: int = 4096
    block_sizes: list[int] | None = None
    cache_mode: Literal["cold", "hot"] = "cold"
    pruning_enabled: bool = True
    dataset_id: int | None = None
    sql: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "seed": self.seed,
            "warmup_runs": self.warmup_runs,
            "repeat_runs": self.repeat_runs,
            "distribution": self.distribution,
            "row_count": self.row_count,
            "block_sizes": self.block_sizes or [65536],
            "cache_mode": self.cache_mode,
            "pruning_enabled": self.pruning_enabled,
            "dataset_id": self.dataset_id,
            "sql": self.sql,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkConfig:
        return cls(
            kind=data.get("kind", "codec"),
            seed=int(data.get("seed", 42)),
            warmup_runs=int(data.get("warmup_runs", 1)),
            repeat_runs=int(data.get("repeat_runs", 3)),
            distribution=data.get("distribution", "run_length"),
            row_count=int(data.get("row_count", 4096)),
            block_sizes=data.get("block_sizes"),
            cache_mode=data.get("cache_mode", "cold"),
            pruning_enabled=bool(data.get("pruning_enabled", True)),
            dataset_id=data.get("dataset_id"),
            sql=data.get("sql"),
        )
