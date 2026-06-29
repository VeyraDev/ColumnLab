from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.engine.benchmark.codec_benchmark import BenchmarkSampleRow
from app.engine.benchmark.config import BenchmarkConfig
from app.engine.benchmark.stats import summarize
from app.engine.cache.block_cache import get_block_cache


@dataclass
class QueryBenchmarkResult:
    samples: list[BenchmarkSampleRow] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def run_query_benchmark(
    config: BenchmarkConfig,
    *,
    execute_fn: Any | None = None,
) -> QueryBenchmarkResult:
    """Run query timing benchmark via injected execute_fn(db-less hook for tests)."""
    if execute_fn is None:
        return QueryBenchmarkResult(
            samples=[],
            summary={
                "kind": "query",
                "message": "query benchmark requires dataset_id and database session",
                "seed": config.seed,
            },
        )

    cache = get_block_cache()
    samples: list[BenchmarkSampleRow] = []
    timed: dict[str, list[float]] = {}
    total_iters = config.warmup_runs + config.repeat_runs

    for iteration in range(total_iters):
        phase = "warmup" if iteration < config.warmup_runs else "timed"
        if config.cache_mode == "cold":
            cache.invalidate_all()
        else:
            execute_fn(warmup=True)

        start = time.perf_counter_ns()
        result = execute_fn(warmup=False)
        elapsed_ns = float(time.perf_counter_ns() - start)

        metric_name = "query.execute_ns"
        extra = json.dumps(
            {
                "cache_mode": config.cache_mode,
                "pruning_enabled": config.pruning_enabled,
                **({k: result.get(k, 0) for k in (
                    "scanned_blocks",
                    "decoded_blocks",
                    "bytes_read",
                    "compressed_operator_blocks",
                    "cache_hits",
                    "block_accesses",
                    "parse_time",
                    "optimize_time",
                    "execute_time",
                    "total_time",
                )} if isinstance(result, dict) else {}),
            },
            sort_keys=True,
        )
        samples.append(
            BenchmarkSampleRow(
                iteration=iteration,
                phase=phase,
                metric_name=metric_name,
                value=elapsed_ns,
                extra_json=extra,
            )
        )
        if phase == "timed":
            timed.setdefault(metric_name, []).append(elapsed_ns)

    summary = {
        "kind": "query",
        "seed": config.seed,
        "cache_mode": config.cache_mode,
        "pruning_enabled": config.pruning_enabled,
        "dataset_id": config.dataset_id,
        "sql": config.sql,
        "metrics": {name: summarize(vals) for name, vals in timed.items()},
    }
    return QueryBenchmarkResult(samples=samples, summary=summary)
