#!/usr/bin/env python3
"""Run the formal codec experiments used by the PPT compression chart.

This script calls ColumnLab's benchmark engine directly, so the frontend and
FastAPI server do not need to be started. It runs the same RAW/RLE/DICTIONARY
codecs for three controlled distributions and writes reproducible CSV, JSON,
and SVG artifacts.

Default formal settings:
- row_count: 100000
- warmup_runs: 3
- repeat_runs: 10
- seed: 42
- target block size metadata: 65536 B

Usage from the repository root:
    python scripts/run_ppt_codec_benchmark.py

Quick smoke run:
    python scripts/run_ppt_codec_benchmark.py --quick
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.engine.benchmark.codec_benchmark import run_codec_benchmark  # noqa: E402
from app.engine.benchmark.config import BenchmarkConfig  # noqa: E402

ENCODINGS = ("RAW", "RLE", "DICTIONARY")
DISTRIBUTIONS = (
    ("run_length", "长游程", "qty", "INT64"),
    ("low_cardinality", "低基数", "region", "UTF8"),
    ("high_cardinality", "高基数", "region", "UTF8"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ColumnLab PPT codec benchmark")
    parser.add_argument("--row-count", type=int, default=100_000)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--block-size", type=int, default=65_536)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "benchmark_output" / "ppt_figure_1",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke test: 10000 rows, no warmup, 2 timed repetitions",
    )
    return parser.parse_args()


def get_stat(metrics: dict[str, Any], key: str, stat: str) -> float:
    record = metrics.get(key)
    if not isinstance(record, dict):
        raise KeyError(f"benchmark metric missing: {key}")
    value = record.get(stat)
    if value is None:
        raise KeyError(f"benchmark stat missing: {key}.{stat}")
    return float(value)


def run_one(
    distribution: str,
    *,
    row_count: int,
    warmup: int,
    repeat: int,
    seed: int,
    block_size: int,
) -> dict[str, Any]:
    print(f"\n[RUN] distribution={distribution}")

    def on_progress(fraction: float, message: str) -> None:
        percent = int(round(fraction * 100))
        print(f"\r      {percent:3d}%  {message:<30}", end="", flush=True)

    config = BenchmarkConfig(
        kind="codec",
        seed=seed,
        warmup_runs=warmup,
        repeat_runs=repeat,
        distribution=distribution,
        row_count=row_count,
        block_sizes=[block_size],
        cache_mode="cold",
        pruning_enabled=False,
    )
    started = time.perf_counter()
    result = run_codec_benchmark(config, on_progress=on_progress)
    elapsed = time.perf_counter() - started
    print(f"\r      done in {elapsed:.2f}s{' ' * 40}")
    return {
        "config": config.to_dict(),
        "elapsed_seconds": elapsed,
        "summary": result.summary,
    }


def build_rows(results: dict[str, dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    ppt_rows: list[dict[str, Any]] = []

    labels = {item[0]: item[1] for item in DISTRIBUTIONS}
    representatives = {item[0]: (item[2], item[3]) for item in DISTRIBUTIONS}

    for distribution, payload in results.items():
        summary = payload["summary"]
        metrics = summary.get("metrics", {})
        for column in ("qty", "region"):
            raw_mean = get_stat(metrics, f"{column}.RAW.encoded_bytes", "mean")
            for encoding in ENCODINGS:
                prefix = f"{column}.{encoding}"
                encoded_mean = get_stat(metrics, f"{prefix}.encoded_bytes", "mean")
                row = {
                    "distribution": distribution,
                    "distribution_label": labels[distribution],
                    "column": column,
                    "encoding": encoding,
                    "encoded_bytes_mean": encoded_mean,
                    "encoded_bytes_median": get_stat(metrics, f"{prefix}.encoded_bytes", "median"),
                    "encoded_bytes_p95": get_stat(metrics, f"{prefix}.encoded_bytes", "p95"),
                    "relative_size_percent": encoded_mean / raw_mean * 100.0 if raw_mean else 0.0,
                    "compression_ratio_mean": get_stat(metrics, f"{prefix}.compression_ratio", "mean"),
                    "encode_ns_median": get_stat(metrics, f"{prefix}.encode_ns", "median"),
                    "decode_ns_median": get_stat(metrics, f"{prefix}.decode_ns", "median"),
                    "row_count": args.row_count,
                    "warmup_runs": args.warmup,
                    "repeat_runs": args.repeat,
                    "seed": args.seed,
                    "block_size_config_bytes": args.block_size,
                }
                all_rows.append(row)

        representative_column, logical_type = representatives[distribution]
        raw_mean = get_stat(metrics, f"{representative_column}.RAW.encoded_bytes", "mean")
        for encoding in ENCODINGS:
            prefix = f"{representative_column}.{encoding}"
            encoded_mean = get_stat(metrics, f"{prefix}.encoded_bytes", "mean")
            ppt_rows.append(
                {
                    "distribution": distribution,
                    "distribution_label": labels[distribution],
                    "representative_column": representative_column,
                    "logical_type": logical_type,
                    "encoding": encoding,
                    "encoded_bytes_mean": encoded_mean,
                    "raw_encoded_bytes_mean": raw_mean,
                    "relative_size_percent": encoded_mean / raw_mean * 100.0 if raw_mean else 0.0,
                    "compression_ratio_mean": get_stat(metrics, f"{prefix}.compression_ratio", "mean"),
                    "row_count": args.row_count,
                    "warmup_runs": args.warmup,
                    "repeat_runs": args.repeat,
                    "seed": args.seed,
                    "block_size_config_bytes": args.block_size,
                }
            )

    return all_rows, ppt_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def nice_max(value: float) -> float:
    if value <= 100:
        return 100.0
    magnitude = 10 ** math.floor(math.log10(value))
    return math.ceil(value / magnitude * 2) / 2 * magnitude


def write_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    width, height = 1600, 900
    margin_left, margin_right = 160, 80
    margin_top, margin_bottom = 145, 165
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    by_group: dict[str, dict[str, float]] = {}
    for row in rows:
        by_group.setdefault(str(row["distribution_label"]), {})[str(row["encoding"])] = float(
            row["relative_size_percent"]
        )

    groups = [item[1] for item in DISTRIBUTIONS]
    maximum = max(100.0, max(v for group in by_group.values() for v in group.values()))
    y_max = nice_max(maximum * 1.12)
    shades = {"RAW": "#D9D9D9", "RLE": "#777777", "DICTIONARY": "#1F1F1F"}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif;fill:#1F2933}.mono{font-family:Consolas,monospace}</style>',
        '<text x="800" y="62" text-anchor="middle" font-size="34" font-weight="700">不同编码的相对存储大小</text>',
        '<text x="800" y="104" text-anchor="middle" font-size="20" fill="#5B6573">RAW = 100%，数值越低表示存储开销越小</text>',
    ]

    # Grid and y axis labels.
    ticks = 5
    for i in range(ticks + 1):
        value = y_max * i / ticks
        y = margin_top + plot_h - plot_h * value / y_max
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width-margin_right}" y2="{y:.1f}" stroke="#E5E7EB" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left-22}" y="{y+7:.1f}" text-anchor="end" font-size="18">{value:.0f}%</text>')

    parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top+plot_h}" stroke="#4B5563" stroke-width="2"/>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top+plot_h}" x2="{width-margin_right}" y2="{margin_top+plot_h}" stroke="#4B5563" stroke-width="2"/>')

    group_w = plot_w / len(groups)
    bar_w = 92
    gap = 22
    cluster_w = len(ENCODINGS) * bar_w + (len(ENCODINGS) - 1) * gap
    for gi, group in enumerate(groups):
        center = margin_left + group_w * (gi + 0.5)
        x0 = center - cluster_w / 2
        for ei, encoding in enumerate(ENCODINGS):
            value = by_group[group][encoding]
            bar_h = plot_h * value / y_max
            x = x0 + ei * (bar_w + gap)
            y = margin_top + plot_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" fill="{shades[encoding]}" stroke="#333333" stroke-width="1"/>'
            )
            label_y = max(margin_top + 18, y - 12)
            parts.append(f'<text x="{x+bar_w/2:.1f}" y="{label_y:.1f}" text-anchor="middle" font-size="18" font-weight="600">{value:.1f}%</text>')
        parts.append(f'<text x="{center:.1f}" y="{margin_top+plot_h+48}" text-anchor="middle" font-size="23" font-weight="600">{escape(group)}</text>')

    legend_y = height - 68
    legend_start = 470
    for i, encoding in enumerate(ENCODINGS):
        x = legend_start + i * 250
        parts.append(f'<rect x="{x}" y="{legend_y-22}" width="34" height="24" fill="{shades[encoding]}" stroke="#333333"/>')
        parts.append(f'<text x="{x+48}" y="{legend_y-2}" font-size="19">{escape(encoding)}</text>')

    parts.append(f'<text x="42" y="{margin_top+plot_h/2}" text-anchor="middle" font-size="20" transform="rotate(-90 42 {margin_top+plot_h/2})">相对存储大小</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def write_readme(path: Path, args: argparse.Namespace) -> None:
    path.write_text(
        "\n".join(
            [
                "# ColumnLab PPT 图1实验结果",
                "",
                "本目录由 `scripts/run_ppt_codec_benchmark.py` 自动生成。",
                "",
                "## 正式参数",
                f"- 行数：{args.row_count}",
                f"- 预热：{args.warmup}",
                f"- 重复：{args.repeat}",
                f"- 随机种子：{args.seed}",
                f"- 块大小配置：{args.block_size} B",
                "- 编码：RAW、RLE、DICTIONARY",
                "- 分布：长游程、低基数、高基数",
                "",
                "## 文件",
                "- `ppt_fig1_codec_relative_size.csv`：PPT图直接使用的数据。",
                "- `ppt_fig1_codec_relative_size.svg`：黑白灰矢量图，可直接插入PPT。",
                "- `codec_benchmark_all_columns.csv`：qty和region全部指标。",
                "- `codec_benchmark_raw.json`：每组benchmark完整summary。",
                "",
                "纵轴采用 `encoded_bytes / RAW encoded_bytes × 100%`，RAW固定为100%。",
                "",
                "注意：当前ColumnLab codec benchmark的 `block_sizes` 字段作为实验配置记录；",
                "编码指标来自当前benchmark引擎对生成列向量的实际RAW/RLE/DICTIONARY编码结果。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def print_summary(rows: list[dict[str, Any]], output_dir: Path) -> None:
    print("\n=== PPT 图1数据 ===")
    for label in [item[1] for item in DISTRIBUTIONS]:
        group = [row for row in rows if row["distribution_label"] == label]
        values = "  ".join(
            f"{row['encoding']}={float(row['relative_size_percent']):.1f}%" for row in group
        )
        winner = min(group, key=lambda row: float(row["relative_size_percent"]))
        print(f"{label:<6} {values}  -> 最小: {winner['encoding']}")
    print(f"\n输出目录: {output_dir}")
    print("PPT可直接插入: ppt_fig1_codec_relative_size.svg")


def main() -> int:
    args = parse_args()
    if args.quick:
        args.row_count = 10_000
        args.warmup = 0
        args.repeat = 2

    if args.row_count < 256:
        raise ValueError("row-count must be >= 256")
    if args.warmup < 0 or args.repeat < 1:
        raise ValueError("warmup must be >= 0 and repeat must be >= 1")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("ColumnLab PPT codec benchmark")
    print(f"rows={args.row_count}, warmup={args.warmup}, repeat={args.repeat}, seed={args.seed}")

    results: dict[str, dict[str, Any]] = {}
    for distribution, _label, _column, _type in DISTRIBUTIONS:
        results[distribution] = run_one(
            distribution,
            row_count=args.row_count,
            warmup=args.warmup,
            repeat=args.repeat,
            seed=args.seed,
            block_size=args.block_size,
        )

    all_rows, ppt_rows = build_rows(results, args)
    write_csv(output_dir / "codec_benchmark_all_columns.csv", all_rows)
    write_csv(output_dir / "ppt_fig1_codec_relative_size.csv", ppt_rows)
    (output_dir / "codec_benchmark_raw.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_svg(output_dir / "ppt_fig1_codec_relative_size.svg", ppt_rows)
    write_readme(output_dir / "README.md", args)
    print_summary(ppt_rows, output_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nbenchmark cancelled", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nbenchmark failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
