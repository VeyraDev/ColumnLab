from __future__ import annotations

from app.engine.benchmark.config import BenchmarkConfig
from app.engine.benchmark.query_benchmark import run_query_benchmark


def test_query_benchmark_summary_includes_counters():
    calls = {"n": 0}

    def execute_fn(*, warmup: bool = False) -> dict:
        calls["n"] += 1
        return {
            "scanned_blocks": 10,
            "decoded_blocks": 2,
            "bytes_read": 4096,
            "compressed_operator_blocks": 3,
            "cache_hits": 1,
            "block_accesses": 11,
        }

    config = BenchmarkConfig(
        kind="query",
        seed=1,
        warmup_runs=0,
        repeat_runs=2,
        dataset_id=1,
        sql="SELECT 1",
    )
    result = run_query_benchmark(config, execute_fn=execute_fn)
    assert "counters" in result.summary
    assert result.summary["counters"]["scanned_blocks"]["mean"] == 10.0
    assert result.summary["counters"]["decoded_blocks"]["mean"] == 2.0
    assert result.summary["counters"]["bytes_read"]["mean"] == 4096.0
    assert calls["n"] == 2
