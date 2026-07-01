#!/usr/bin/env python3
"""Generate the remaining three ColumnLab PPT performance figures.

Outputs:
- Figure 2: block pruning on/off (latency + scanned blocks + bytes read)
- Figure 3: compressed operators vs full decoding (RLE SUM + Dictionary GROUP BY)
- Figure 4: block size sensitivity (storage ratio + query latency)

The script uses the real ColumnLab backend API for query experiments and the
real codec implementations for compressed-operator microbenchmarks.

Before running, start the backend at http://127.0.0.1:8000.

Quick run (default):
    python scripts/run_ppt_remaining_benchmarks.py

Formal run:
    python scripts/run_ppt_remaining_benchmarks.py --formal
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise SystemExit("缺少 httpx，请先执行 backend 环境中的 pip install -r requirements.txt") from exc

from app.engine.benchmark.synthetic import generate_dataset  # noqa: E402
from app.engine.codecs.base import AggregateOp  # noqa: E402
from app.engine.codecs.dictionary import DictionaryCodec  # noqa: E402
from app.engine.codecs.rle import RleCodec  # noqa: E402
from app.engine.vectors import ValueVector  # noqa: E402

BASE_API = "http://127.0.0.1:8000/api"
BLOCK_SIZES = [16_384, 32_768, 65_536, 131_072, 262_144]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run remaining ColumnLab PPT benchmarks")
    parser.add_argument("--base-api", default=BASE_API)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmark_output" / "ppt_remaining")
    parser.add_argument("--formal", action="store_true", help="100k rows, warmup=3, repeat=10")
    parser.add_argument("--keep-datasets", action="store_true", help="保留脚本导入的临时数据集")
    return parser.parse_args()


def percentile95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)
    return float(ordered[idx])


def stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "p95": 0.0, "stdev": 0.0}
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p95": percentile95(values),
        "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def api_data(resp: httpx.Response) -> Any:
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("msg") or payload)
    return payload.get("data")


def register_user(client: httpx.Client) -> dict[str, str]:
    stamp = int(time.time() * 1000)
    username = f"ppt_bench_{stamp}"
    password = "columnlab12"
    data = api_data(
        client.post(
            "/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": password},
        )
    )
    return {"Authorization": f"Bearer {data['access_token']}"}


def wait_import(client: httpx.Client, headers: dict[str, str], job_id: int, timeout: float = 600.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = api_data(client.get(f"/import-jobs/{job_id}", headers=headers))
        if job["status"] in {"completed", "failed", "cancelled"}:
            if job["status"] != "completed":
                raise RuntimeError(f"导入失败: {job}")
            return job
        print(
            f"\r      import {job.get('stage', '—'):<12} rows={job.get('rows_processed', 0):>8}",
            end="",
            flush=True,
        )
        time.sleep(0.4)
    raise TimeoutError(f"等待导入任务 {job_id} 超时")


def upload_csv(
    client: httpx.Client,
    headers: dict[str, str],
    path: Path,
    *,
    block_size: int,
) -> int:
    print(f"\n[IMPORT] {path.name}, block={block_size // 1024} KiB")
    with path.open("rb") as fh:
        resp = client.post(
            "/datasets/uploads",
            headers=headers,
            files={"file": (path.name, fh, "text/csv")},
            data={
                "table_name": "data",
                "import_mode": "strict",
                "schema_overrides": "[]",
                "target_block_bytes": str(block_size),
            },
            timeout=180.0,
        )
    result = api_data(resp)
    wait_import(client, headers, int(result["job_id"]))
    print("\r      import completed" + " " * 45)
    return int(result["dataset_id"])


def wait_benchmark(client: httpx.Client, headers: dict[str, str], run_id: int, timeout: float = 900.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = api_data(client.get(f"/benchmarks/{run_id}", headers=headers))
        if run["status"] in {"completed", "failed", "cancelled"}:
            if run["status"] != "completed":
                raise RuntimeError(f"benchmark失败: {run.get('error_message')}")
            return run
        snap = api_data(client.get(f"/benchmarks/{run_id}/progress", headers=headers))
        progress = float(snap.get("progress") or 0.0)
        print(
            f"\r      benchmark {progress * 100:5.1f}% {snap.get('message') or 'running':<35}",
            end="",
            flush=True,
        )
        time.sleep(0.5)
    raise TimeoutError(f"等待 benchmark {run_id} 超时")


def run_query_benchmark(
    client: httpx.Client,
    headers: dict[str, str],
    *,
    dataset_id: int,
    sql: str,
    pruning: bool,
    warmup: int,
    repeat: int,
    cache_mode: str = "cold",
) -> dict[str, Any]:
    print(f"\n[BENCH] dataset={dataset_id}, pruning={pruning}, cache={cache_mode}")
    run = api_data(
        client.post(
            "/benchmarks",
            headers=headers,
            json={
                "kind": "query",
                "seed": 42,
                "warmup_runs": warmup,
                "repeat_runs": repeat,
                "distribution": "mixed_business",
                "row_count": 4096,
                "block_sizes": [65_536],
                "cache_mode": cache_mode,
                "pruning_enabled": pruning,
                "dataset_id": dataset_id,
                "sql": sql,
            },
        )
    )
    completed = wait_benchmark(client, headers, int(run["id"]))
    print("\r      benchmark completed" + " " * 45)
    return completed["summary"]


def generate_pruning_csv(path: Path, rows: int) -> None:
    # Three clustered regions. AND result is zero; OR result selects 50%.
    one_quarter = rows // 4
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "region", "amount", "category"])
        for i in range(rows):
            if i < one_quarter:
                region, amount, category = "north", i % 1000, "A"
            elif i < 2 * one_quarter:
                region, amount, category = "south", 2500 + (i % 1000), "B"
            else:
                region, amount, category = "south", i % 1000, "C"
            writer.writerow([i + 1, region, amount, category])


def generate_orders_csv(path: Path, rows: int, seed: int = 42) -> None:
    rng = random.Random(seed)
    regions = ["东北", "华东", "华中", "华北", "华南", "西南"]
    categories = ["办公", "家电", "数码", "食品", "服饰"]
    channels = ["线上", "门店", "分销"]
    # Status is deliberately clustered so pruning can react to block boundaries.
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["order_id", "region", "status", "category", "channel", "quantity", "amount"])
        for i in range(rows):
            fraction = i / max(1, rows)
            if fraction < 0.60:
                status = "已完成"
            elif fraction < 0.80:
                status = "处理中"
            else:
                status = "已取消"
            quantity = rng.randint(1, 8)
            amount = round(quantity * rng.uniform(15, 900), 2)
            writer.writerow(
                [
                    f"O{i + 1:08d}",
                    regions[i % len(regions)],
                    status,
                    categories[rng.randrange(len(categories))],
                    channels[rng.randrange(len(channels))],
                    quantity,
                    f"{amount:.2f}",
                ]
            )


def metric_stat(summary: dict[str, Any], section: str, name: str, stat: str = "median") -> float:
    block = summary.get(section, {}).get(name, {})
    return float(block.get(stat, 0.0))


def dataset_storage(client: httpx.Client, headers: dict[str, str], dataset_id: int) -> dict[str, float]:
    tables = api_data(client.get(f"/datasets/{dataset_id}/tables", headers=headers))
    if not tables:
        raise RuntimeError(f"数据集 {dataset_id} 没有表")
    columns = api_data(client.get(f"/tables/{tables[0]['id']}/columns", headers=headers))
    raw_bytes = float(sum(int(c.get("raw_bytes") or 0) for c in columns))
    encoded_bytes = float(sum(int(c.get("encoded_bytes") or 0) for c in columns))
    return {
        "raw_bytes": raw_bytes,
        "encoded_bytes": encoded_bytes,
        "relative_size_percent": encoded_bytes / raw_bytes * 100.0 if raw_bytes else 0.0,
        "block_count": float(sum(int(c.get("block_count") or 0) for c in columns)),
    }


def measure_ns(fn: Callable[[], Any], warmup: int, repeat: int) -> dict[str, float]:
    for _ in range(warmup):
        fn()
    values: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter_ns()
        fn()
        values.append(float(time.perf_counter_ns() - start))
    return stats(values)


def compressed_operator_benchmark(row_count: int, warmup: int, repeat: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    run_ds = generate_dataset("run_length", row_count, seed=42)
    run_vec = ValueVector.from_typed(run_ds["logical_types"]["qty"], run_ds["qty"])
    rle_block = RleCodec.encode(run_vec, run_vec.null_bitmap())

    def rle_compressed() -> Any:
        return RleCodec.aggregate(rle_block, AggregateOp.SUM)

    def rle_decode() -> int:
        decoded = RleCodec.decode(rle_block)
        return sum(v for v in decoded.values if v is not None)

    for mode, fn in (("压缩态执行", rle_compressed), ("完整解码", rle_decode)):
        record = measure_ns(fn, warmup, repeat)
        rows.append({"case": "RLE SUM", "mode": mode, **record})

    dict_ds = generate_dataset("low_cardinality", row_count, seed=42)
    dict_vec = ValueVector.from_typed(dict_ds["logical_types"]["region"], dict_ds["region"])
    dict_block = DictionaryCodec.encode(dict_vec, dict_vec.null_bitmap())

    def dict_compressed() -> dict[int, int]:
        return DictionaryCodec.group_by_codes(dict_block)

    def dict_decode() -> Counter[Any]:
        decoded = DictionaryCodec.decode(dict_block)
        return Counter(v for v in decoded.values if v is not None)

    for mode, fn in (("压缩态执行", dict_compressed), ("完整解码", dict_decode)):
        record = measure_ns(fn, warmup, repeat)
        rows.append({"case": "Dictionary GROUP BY", "mode": mode, **record})

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def svg_begin(title: str, subtitle: str) -> list[str]:
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
        '<rect width="1600" height="900" fill="#FFFFFF"/>',
        '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif;fill:#1F2933}.small{font-size:16px}.label{font-size:19px}.title{font-size:34px;font-weight:700}.subtitle{font-size:19px;fill:#5B6573}</style>',
        f'<text x="800" y="58" text-anchor="middle" class="title">{escape(title)}</text>',
        f'<text x="800" y="96" text-anchor="middle" class="subtitle">{escape(subtitle)}</text>',
    ]


def draw_bar_panel(parts: list[str], x: float, y: float, w: float, h: float, title: str, labels: list[str], values: list[float], unit: str, y_max: float | None = None) -> None:
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" stroke="#D1D5DB"/>')
    parts.append(f'<text x="{x+24}" y="{y+38}" font-size="22" font-weight="700">{escape(title)}</text>')
    left, right, top, bottom = x + 75, x + w - 30, y + 75, y + h - 72
    max_v = y_max or max(values or [1]) * 1.18
    max_v = max(max_v, 1e-9)
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#4B5563" stroke-width="2"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#4B5563" stroke-width="2"/>')
    group_w = (right - left) / max(1, len(labels))
    bar_w = min(120, group_w * 0.48)
    shades = ["#555555", "#CFCFCF", "#888888", "#222222", "#AAAAAA"]
    for i, (label, value) in enumerate(zip(labels, values)):
        cx = left + group_w * (i + 0.5)
        bh = (bottom - top) * value / max_v
        bx, by = cx - bar_w / 2, bottom - bh
        parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{shades[i % len(shades)]}" stroke="#222"/>')
        parts.append(f'<text x="{cx:.1f}" y="{max(top+20, by-10):.1f}" text-anchor="middle" font-size="17" font-weight="600">{value:.2f}{escape(unit)}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{bottom+32}" text-anchor="middle" font-size="17">{escape(label)}</text>')


def write_figure2(path: Path, rows: list[dict[str, Any]]) -> None:
    parts = svg_begin("块裁剪对查询执行的影响", "相同SQL、冷缓存；比较裁剪关闭与开启")
    labels = ["关闭裁剪", "开启裁剪"]
    latency = [float(r["median_ms"]) for r in rows]
    scanned = [float(r["scanned_blocks"]) for r in rows]
    bytes_mb = [float(r["bytes_read"]) / 1024 / 1024 for r in rows]
    draw_bar_panel(parts, 70, 135, 700, 600, "查询延迟（中位数）", labels, latency, " ms")
    draw_bar_panel(parts, 830, 135, 700, 275, "实际扫描块数", labels, scanned, "")
    draw_bar_panel(parts, 830, 460, 700, 275, "读取数据量", labels, bytes_mb, " MiB")
    parts.append('<text x="800" y="825" text-anchor="middle" font-size="17" fill="#5B6573">裁剪收益应同时由耗时与实际扫描量解释，而不是只比较单次耗时。</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def write_figure3(path: Path, rows: list[dict[str, Any]]) -> None:
    parts = svg_begin("压缩态算子与完整解码对比", "RLE SUM 与 Dictionary GROUP BY 微基准；中位数与P95")
    cases = ["RLE SUM", "Dictionary GROUP BY"]
    modes = ["完整解码", "压缩态执行"]
    x0, y0, plot_w, plot_h = 150, 165, 1320, 520
    max_ms = max(float(r["p95"]) / 1e6 for r in rows) * 1.18
    parts.append(f'<line x1="{x0}" y1="{y0+plot_h}" x2="{x0+plot_w}" y2="{y0+plot_h}" stroke="#4B5563" stroke-width="2"/>')
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+plot_h}" stroke="#4B5563" stroke-width="2"/>')
    for i in range(6):
        val = max_ms * i / 5
        yy = y0 + plot_h - plot_h * i / 5
        parts.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x0+plot_w}" y2="{yy:.1f}" stroke="#E5E7EB"/>')
        parts.append(f'<text x="{x0-20}" y="{yy+6:.1f}" text-anchor="end" font-size="16">{val:.1f}</text>')
    group_w = plot_w / 2
    bar_w, gap = 145, 34
    shade = {"完整解码": "#CFCFCF", "压缩态执行": "#333333"}
    lookup = {(r["case"], r["mode"]): r for r in rows}
    for ci, case in enumerate(cases):
        center = x0 + group_w * (ci + 0.5)
        for mi, mode in enumerate(modes):
            row = lookup[(case, mode)]
            med = float(row["median"]) / 1e6
            p95 = float(row["p95"]) / 1e6
            bx = center + (mi - 0.5) * (bar_w + gap) - bar_w / 2
            bh = plot_h * med / max_ms
            by = y0 + plot_h - bh
            parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bh:.1f}" fill="{shade[mode]}" stroke="#222"/>')
            py = y0 + plot_h - plot_h * p95 / max_ms
            parts.append(f'<line x1="{bx+bar_w/2:.1f}" y1="{by:.1f}" x2="{bx+bar_w/2:.1f}" y2="{py:.1f}" stroke="#111" stroke-width="3"/>')
            parts.append(f'<line x1="{bx+bar_w/2-18:.1f}" y1="{py:.1f}" x2="{bx+bar_w/2+18:.1f}" y2="{py:.1f}" stroke="#111" stroke-width="3"/>')
            parts.append(f'<text x="{bx+bar_w/2:.1f}" y="{max(y0+20, by-12):.1f}" text-anchor="middle" font-size="17" font-weight="600">{med:.2f} ms</text>')
        parts.append(f'<text x="{center:.1f}" y="{y0+plot_h+45}" text-anchor="middle" font-size="22" font-weight="700">{escape(case)}</text>')
    parts.append('<rect x="550" y="770" width="34" height="24" fill="#CFCFCF" stroke="#222"/><text x="596" y="790" font-size="19">完整解码</text>')
    parts.append('<rect x="815" y="770" width="34" height="24" fill="#333333" stroke="#222"/><text x="861" y="790" font-size="19">压缩态执行</text>')
    parts.append('<text x="42" y="425" text-anchor="middle" font-size="19" transform="rotate(-90 42 425)">执行时间（ms）</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def draw_line_panel(parts: list[str], x: float, y: float, w: float, h: float, title: str, xs: list[float], ys: list[float], y_label: str, value_suffix: str) -> None:
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" stroke="#D1D5DB"/>')
    parts.append(f'<text x="{x+24}" y="{y+38}" font-size="22" font-weight="700">{escape(title)}</text>')
    left, right, top, bottom = x + 82, x + w - 35, y + 75, y + h - 72
    min_y, max_y = min(ys), max(ys)
    pad = max((max_y - min_y) * 0.18, max(abs(max_y), 1) * 0.05)
    lo, hi = max(0, min_y - pad), max_y + pad
    if hi <= lo:
        hi = lo + 1
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#4B5563" stroke-width="2"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#4B5563" stroke-width="2"/>')
    points: list[str] = []
    for i, (xv, yv) in enumerate(zip(xs, ys)):
        px = left + (right - left) * i / max(1, len(xs) - 1)
        py = bottom - (bottom - top) * (yv - lo) / (hi - lo)
        points.append(f"{px:.1f},{py:.1f}")
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="#333333"/>')
        parts.append(f'<text x="{px:.1f}" y="{py-15:.1f}" text-anchor="middle" font-size="16" font-weight="600">{yv:.2f}{escape(value_suffix)}</text>')
        parts.append(f'<text x="{px:.1f}" y="{bottom+32}" text-anchor="middle" font-size="16">{int(xv)} KiB</text>')
    parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#333333" stroke-width="4"/>')
    parts.append(f'<text x="{x+24}" y="{y+h-22}" font-size="15" fill="#5B6573">{escape(y_label)}</text>')


def write_figure4(path: Path, rows: list[dict[str, Any]]) -> None:
    parts = svg_begin("目标块大小对存储与查询的影响", "相同数据与SQL；分别导入16、32、64、128、256 KiB版本")
    xs = [float(r["block_size_kib"]) for r in rows]
    storage = [float(r["relative_size_percent"]) for r in rows]
    latency = [float(r["median_ms"]) for r in rows]
    draw_line_panel(parts, 70, 145, 700, 600, "块大小—相对存储大小", xs, storage, "编码后字节数 / 原始字节数", "%")
    draw_line_panel(parts, 830, 145, 700, 600, "块大小—查询延迟", xs, latency, "冷缓存、中位数", " ms")
    parts.append('<text x="800" y="825" text-anchor="middle" font-size="17" fill="#5B6573">小块提高裁剪粒度但增加块头与调度开销；大块减少块数但可能读取更多无关数据。</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if args.formal:
        pruning_rows, order_rows = 24_000, 100_000
        warmup, repeat = 3, 10
        codec_rows, codec_repeat = 100_000, 10
    else:
        pruning_rows, order_rows = 12_000, 20_000
        warmup, repeat = 1, 3
        codec_rows, codec_repeat = 50_000, 5

    print("[1/3] 压缩态算子微基准")
    figure3_rows = compressed_operator_benchmark(codec_rows, warmup, codec_repeat)
    write_csv(output / "ppt_fig3_compressed_vs_decode.csv", figure3_rows)
    write_figure3(output / "图3-15_压缩态执行与完整解码.svg", figure3_rows)

    client = httpx.Client(base_url=args.base_api.rstrip("/"), timeout=180.0)
    try:
        health_url = args.base_api.rstrip("/").removesuffix("/api") + "/health"
        health = httpx.get(health_url, timeout=10.0)
        health.raise_for_status()
    except Exception as exc:
        print("\n后端未启动，已生成图3的压缩态算子数据。")
        print("请先运行 scripts/start.ps1，再重新执行本脚本生成图2和图4。")
        raise SystemExit(2) from exc

    headers = register_user(client)
    imported_ids: list[int] = []
    raw_results: dict[str, Any] = {"mode": "formal" if args.formal else "quick"}

    with tempfile.TemporaryDirectory(prefix="columnlab-ppt-") as tmp:
        temp = Path(tmp)

        print("\n[2/3] 块裁剪开关实验")
        pruning_csv = temp / "ppt_pruning_multicolumn.csv"
        generate_pruning_csv(pruning_csv, pruning_rows)
        pruning_dataset = upload_csv(client, headers, pruning_csv, block_size=4096)
        imported_ids.append(pruning_dataset)
        pruning_sql = "SELECT COUNT(*) AS n FROM data WHERE amount >= 2500 AND region = 'north'"
        figure2_rows: list[dict[str, Any]] = []
        for enabled in (False, True):
            summary = run_query_benchmark(
                client,
                headers,
                dataset_id=pruning_dataset,
                sql=pruning_sql,
                pruning=enabled,
                warmup=warmup,
                repeat=repeat,
            )
            figure2_rows.append(
                {
                    "pruning": "开启裁剪" if enabled else "关闭裁剪",
                    "median_ms": metric_stat(summary, "metrics", "query.execute_ns") / 1e6,
                    "p95_ms": metric_stat(summary, "metrics", "query.execute_ns", "p95") / 1e6,
                    "scanned_blocks": metric_stat(summary, "counters", "scanned_blocks"),
                    "decoded_blocks": metric_stat(summary, "counters", "decoded_blocks"),
                    "bytes_read": metric_stat(summary, "counters", "bytes_read"),
                    "compressed_operator_blocks": metric_stat(summary, "counters", "compressed_operator_blocks"),
                    "cache_hits": metric_stat(summary, "counters", "cache_hits"),
                    "repeat_runs": repeat,
                    "warmup_runs": warmup,
                    "row_count": pruning_rows,
                    "sql": pruning_sql,
                }
            )
            raw_results[f"pruning_{enabled}"] = summary
        write_csv(output / "ppt_fig2_pruning.csv", figure2_rows)
        write_figure2(output / "图3-14_块裁剪对查询执行的影响.svg", figure2_rows)

        print("\n[3/3] 块大小敏感性实验")
        orders_csv = temp / "ppt_orders.csv"
        generate_orders_csv(orders_csv, order_rows)
        figure4_rows: list[dict[str, Any]] = []
        block_sql = "SELECT region, COUNT(*) AS c FROM data WHERE status = '已完成' GROUP BY region ORDER BY region"
        for block_size in BLOCK_SIZES:
            dataset_id = upload_csv(client, headers, orders_csv, block_size=block_size)
            imported_ids.append(dataset_id)
            storage = dataset_storage(client, headers, dataset_id)
            summary = run_query_benchmark(
                client,
                headers,
                dataset_id=dataset_id,
                sql=block_sql,
                pruning=True,
                warmup=warmup,
                repeat=repeat,
            )
            figure4_rows.append(
                {
                    "block_size_bytes": block_size,
                    "block_size_kib": block_size // 1024,
                    **storage,
                    "median_ms": metric_stat(summary, "metrics", "query.execute_ns") / 1e6,
                    "p95_ms": metric_stat(summary, "metrics", "query.execute_ns", "p95") / 1e6,
                    "scanned_blocks": metric_stat(summary, "counters", "scanned_blocks"),
                    "decoded_blocks": metric_stat(summary, "counters", "decoded_blocks"),
                    "bytes_read": metric_stat(summary, "counters", "bytes_read"),
                    "repeat_runs": repeat,
                    "warmup_runs": warmup,
                    "row_count": order_rows,
                    "sql": block_sql,
                }
            )
            raw_results[f"block_{block_size}"] = summary
        write_csv(output / "ppt_fig4_block_size.csv", figure4_rows)
        write_figure4(output / "图3-16_块大小对存储与查询的影响.svg", figure4_rows)

    (output / "benchmark_raw.json").write_text(
        json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "\n".join(
            [
                "# ColumnLab PPT剩余性能图",
                "",
                f"模式：{'formal' if args.formal else 'quick'}",
                f"查询预热/重复：{warmup}/{repeat}",
                f"压缩算子行数：{codec_rows}",
                f"裁剪数据行数：{pruning_rows}",
                f"块大小数据行数：{order_rows}",
                "",
                "- 图3-14_块裁剪对查询执行的影响.svg",
                "- 图3-15_压缩态执行与完整解码.svg",
                "- 图3-16_块大小对存储与查询的影响.svg",
                "- 对应CSV与benchmark_raw.json",
                "",
                "说明：图3-15使用真实RLE SUM与Dictionary GROUP BY编码态算子，",
                "并以同一编码块完整解码后再计算作为基线。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    if not args.keep_datasets:
        for dataset_id in imported_ids:
            try:
                client.delete(f"/datasets/{dataset_id}", headers=headers)
            except Exception:
                pass

    print(f"\n完成，输出目录：{output}")
    for name in (
        "图3-14_块裁剪对查询执行的影响.svg",
        "图3-15_压缩态执行与完整解码.svg",
        "图3-16_块大小对存储与查询的影响.svg",
    ):
        print(f"  {name}")
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
