from __future__ import annotations

import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.engine.benchmark.config import BenchmarkConfig
from app.engine.benchmark.row_baseline import benchmark_row_baseline, rows_from_columns
from app.engine.benchmark.stats import summarize
from app.engine.benchmark.synthetic import generate_dataset
from app.engine.codecs.base import AggregateOp, PredicateEq, PredicateRange
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.types import Encoding
from app.engine.vectors import ValueVector

CODECS = {
    Encoding.RAW: RawCodec,
    Encoding.RLE: RleCodec,
    Encoding.DICTIONARY: DictionaryCodec,
}


@dataclass
class BenchmarkSampleRow:
    iteration: int
    phase: str
    metric_name: str
    value: float
    extra_json: str | None = None


@dataclass
class CodecBenchmarkResult:
    samples: list[BenchmarkSampleRow] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def run_codec_benchmark(
    config: BenchmarkConfig,
    *,
    on_progress: Callable[[float, str], None] | None = None,
) -> CodecBenchmarkResult:
    dataset = generate_dataset(config.distribution, config.row_count, seed=config.seed)
    qty_vector = ValueVector.from_typed(dataset["logical_types"]["qty"], dataset["qty"])
    nulls = qty_vector.null_bitmap()
    region_vector = ValueVector.from_typed(dataset["logical_types"]["region"], dataset["region"])
    region_nulls = region_vector.null_bitmap()

    rows = rows_from_columns({"qty": dataset["qty"], "region": dataset["region"]})
    non_null_qty = [v for v in dataset["qty"] if v is not None]
    eq_target_qty = non_null_qty[len(non_null_qty) // 2] if non_null_qty else 0
    non_null_region = [v for v in dataset["region"] if v is not None]
    eq_target_region = non_null_region[len(non_null_region) // 2] if non_null_region else "north"
    lo = min(non_null_qty) if non_null_qty else 0
    hi = max(non_null_qty) if non_null_qty else 0

    samples: list[BenchmarkSampleRow] = []
    timed_metrics: dict[str, list[float]] = {}

    column_targets = {
        "qty": (eq_target_qty, lo, hi),
        "region": (eq_target_region, None, None),
    }
    vectors = [("qty", qty_vector, nulls), ("region", region_vector, region_nulls)]
    total_iters = config.warmup_runs + config.repeat_runs

    for iteration in range(total_iters):
        phase = "warmup" if iteration < config.warmup_runs else "timed"
        if on_progress is not None:
            on_progress(
                (iteration + 1) / total_iters,
                f"codec 迭代 {iteration + 1}/{total_iters}",
            )
        for col_name, vector, col_nulls in vectors:
            eq_target, lo_bound, hi_bound = column_targets[col_name]
            for encoding, codec in CODECS.items():
                enc_name = encoding.name
                tracemalloc.start()
                block = codec.encode(vector, col_nulls)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                decoded = codec.decode(block)
                assert decoded.length == vector.length

                ratio = 0.0 if block.raw_bytes == 0 else 1.0 - (block.encoded_bytes / block.raw_bytes)
                metrics = {
                    f"{col_name}.{enc_name}.encoded_bytes": float(block.encoded_bytes),
                    f"{col_name}.{enc_name}.compression_ratio": ratio,
                    f"{col_name}.{enc_name}.encode_ns": float(block.encode_ns),
                    f"{col_name}.{enc_name}.decode_ns": float(
                        _measure_decode_ns(codec, block)
                    ),
                    f"{col_name}.{enc_name}.peak_memory_bytes": float(peak),
                }

                caps = codec.estimate_capabilities()
                if caps.supports_filter:
                    metrics[f"{col_name}.{enc_name}.filter_eq_ns"] = _measure_filter_eq_ns(
                        codec, block, eq_target
                    )
                    if lo_bound is not None and hi_bound is not None:
                        metrics[f"{col_name}.{enc_name}.filter_range_ns"] = _measure_filter_range_ns(
                            codec, block, lo_bound, hi_bound
                        )
                if caps.supports_aggregate:
                    metrics[f"{col_name}.{enc_name}.aggregate_sum_ns"] = _measure_aggregate_ns(
                        codec, block
                    )

                for name, value in metrics.items():
                    samples.append(
                        BenchmarkSampleRow(
                            iteration=iteration,
                            phase=phase,
                            metric_name=name,
                            value=value,
                        )
                    )
                    if phase == "timed":
                        timed_metrics.setdefault(name, []).append(value)

        row_metrics = benchmark_row_baseline(rows, eq_target=eq_target_qty, range_bounds=(lo, hi))
        for name, value in row_metrics.items():
            samples.append(
                BenchmarkSampleRow(
                    iteration=iteration,
                    phase=phase,
                    metric_name=name,
                    value=value,
                )
            )
            if phase == "timed":
                timed_metrics.setdefault(name, []).append(value)

    summary_metrics = {name: summarize(vals) for name, vals in timed_metrics.items()}
    summary = {
        "kind": "codec",
        "distribution": config.distribution,
        "row_count": config.row_count,
        "seed": config.seed,
        "warmup_runs": config.warmup_runs,
        "repeat_runs": config.repeat_runs,
        "metrics": summary_metrics,
        "comparison": _build_comparison(summary_metrics),
    }
    return CodecBenchmarkResult(samples=samples, summary=summary)


def _measure_decode_ns(codec: type, block: Any) -> float:
    import time

    start = time.perf_counter_ns()
    codec.decode(block)
    return float(time.perf_counter_ns() - start)


def _measure_filter_eq_ns(codec: type, block: Any, target: Any) -> float:
    import time

    start = time.perf_counter_ns()
    codec.filter(block, PredicateEq(target))
    return float(time.perf_counter_ns() - start)


def _measure_filter_range_ns(codec: type, block: Any, lo: Any, hi: Any) -> float:
    import time

    start = time.perf_counter_ns()
    codec.filter(block, PredicateRange(lower=lo, upper=hi))
    return float(time.perf_counter_ns() - start)


def _measure_aggregate_ns(codec: type, block: Any) -> float:
    import time

    start = time.perf_counter_ns()
    codec.aggregate(block, AggregateOp.SUM)
    return float(time.perf_counter_ns() - start)


def _build_comparison(summary_metrics: dict[str, dict[str, float]]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for col in ("qty", "region"):
        raw_bytes = summary_metrics.get(f"{col}.RAW.encoded_bytes", {}).get("mean")
        rle_bytes = summary_metrics.get(f"{col}.RLE.encoded_bytes", {}).get("mean")
        dict_bytes = summary_metrics.get(f"{col}.DICTIONARY.encoded_bytes", {}).get("mean")
        if raw_bytes and rle_bytes:
            comparison[f"{col}.rle_vs_raw_bytes_ratio"] = rle_bytes / raw_bytes if raw_bytes else 0
        if raw_bytes and dict_bytes:
            comparison[f"{col}.dict_vs_raw_bytes_ratio"] = dict_bytes / raw_bytes if raw_bytes else 0
    return comparison
