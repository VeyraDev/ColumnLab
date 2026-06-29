from __future__ import annotations

from app.engine.benchmark.codec_benchmark import run_codec_benchmark
from app.engine.benchmark.config import BenchmarkConfig


def test_rle_smaller_than_raw_on_run_length():
    config = BenchmarkConfig(
        kind="codec",
        seed=42,
        warmup_runs=0,
        repeat_runs=2,
        distribution="run_length",
        row_count=2048,
    )
    result = run_codec_benchmark(config)
    comparison = result.summary["comparison"]
    assert comparison["qty.rle_vs_raw_bytes_ratio"] < 1.0
    metrics = result.summary["metrics"]
    assert "qty.RLE.encoded_bytes" in metrics
    assert "mean" in metrics["qty.RLE.encoded_bytes"]
    assert "p95" in metrics["qty.RLE.encoded_bytes"]


def test_codec_benchmark_only_timed_in_summary():
    config = BenchmarkConfig(warmup_runs=1, repeat_runs=2, row_count=512)
    result = run_codec_benchmark(config)
    timed = [s for s in result.samples if s.phase == "timed"]
    warmup = [s for s in result.samples if s.phase == "warmup"]
    assert len(warmup) > 0
    assert len(timed) > 0
    for name, stats in result.summary["metrics"].items():
        assert stats["count"] == 2.0
