#!/usr/bin/env python3
"""API-level demo flow for ColumnLab defense presentation."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
BASE = "http://127.0.0.1:8000/api"


def step(n: int, title: str) -> None:
    print(f"\n[{n:02d}] {title}")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=120.0)
    username = f"demo_{int(time.time())}"
    password = "secret12"

    step(1, "Register user")
    r = client.post("/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password})
    token = r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    step(2, "Health check")
    assert httpx.get("http://127.0.0.1:8000/health").json()["status"] == "ok"

    step(3, "Upload demo_rle.csv")
    with (SAMPLES / "demo_rle.csv").open("rb") as fh:
        up = client.post(
            "/datasets/uploads",
            headers=headers,
            files={"file": ("demo_rle.csv", fh, "text/csv")},
            data={"table_name": "data", "import_mode": "strict", "target_block_bytes": "512"},
        )
    job_id = up.json()["data"]["job_id"]
    dataset_id = up.json()["data"]["dataset_id"]

    step(4, "Wait import job")
    for _ in range(60):
        job = client.get(f"/import-jobs/{job_id}", headers=headers).json()["data"]
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(0.3)
    assert job["status"] == "completed", job

    step(5, "Fetch dataset + storage map")
    ds = client.get(f"/datasets/{dataset_id}", headers=headers).json()["data"]
    tables = client.get(f"/datasets/{dataset_id}/tables", headers=headers).json()["data"]
    smap = client.get(f"/tables/{tables[0]['id']}/storage-map", headers=headers).json()["data"]
    print(f"  rows={ds['row_count']} columns={smap['column_count']}")

    step(6, "Block preview (RLE/DICT insight)")
    cols = client.get(f"/tables/{tables[0]['id']}/columns", headers=headers).json()["data"]
    preview = client.get(f"/columns/{cols[0]['id']}/blocks/0/preview", headers=headers).json()["data"]
    print(f"  winner={preview.get('winner_encoding')}")

    step(7, "Submit SQL query")
    q = client.post(
        "/queries",
        headers=headers,
        json={"dataset_id": dataset_id, "table_id": tables[0]["id"], "sql": "SELECT COUNT(*) AS cnt FROM data"},
    ).json()["data"]
    query_id = q["query_id"]

    step(8, "Poll query result")
    for _ in range(60):
        st = client.get(f"/queries/{query_id}", headers=headers).json()["data"]
        if st["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.2)
    assert st["status"] == "completed"

    step(9, "Submit codec benchmark")
    bench = client.post(
        "/benchmarks",
        headers=headers,
        json={"kind": "codec", "seed": 7, "warmup_runs": 0, "repeat_runs": 2, "row_count": 1024},
    ).json()["data"]
    run_id = bench["id"]

    step(10, "Wait benchmark + export summary")
    for _ in range(60):
        br = client.get(f"/benchmarks/{run_id}", headers=headers).json()["data"]
        if br["status"] in {"completed", "failed"}:
            break
        time.sleep(0.4)
    assert br["status"] == "completed"
    summary = br["summary"]
    print(f"  metrics={len(summary.get('metrics', {}))} seed={summary.get('seed')}")

    step(11, "Runtime stats")
    rt = client.get("/runtime", headers=headers).json()["data"]
    print(json.dumps({"cpu_percent": rt.get("cpu_percent"), "memory_mb": rt.get("memory_mb")}, indent=2))

    print("\nDemo flow completed OK.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Demo flow failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
