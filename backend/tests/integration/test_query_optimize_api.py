from __future__ import annotations

import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "opt_user", "email": "opt@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "opt_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wait_job(client, headers, job_id: int, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/import-jobs/{job_id}", headers=headers)
        body = resp.json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("import job did not finish")


def _import_sample(client, headers) -> tuple[int, int]:
    with (SAMPLES / "basic.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("basic.csv", fh, "text/csv")},
            data={"table_name": "data", "import_mode": "strict", "target_block_bytes": "512"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    job = _wait_job(client, headers, data["job_id"])
    assert job["status"] == "completed"
    tables = client.get(f"/api/datasets/{data['dataset_id']}/tables", headers=headers).json()["data"]
    return data["dataset_id"], tables[0]["id"]


def test_query_optimize_explain(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    dataset_id, table_id = _import_sample(client, headers)

    resp = client.post(
        "/api/queries",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "table_id": table_id,
            "sql": "SELECT id FROM data WHERE id > 100 LIMIT 10",
        },
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "running"
    assert body["total_blocks"] > 0

    query_id = body["query_id"]
    deadline = time.time() + 30
    while time.time() < deadline:
        st = client.get(f"/api/queries/{query_id}", headers=headers).json()["data"]
        if st["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.2)
    assert st["status"] == "completed"

    explain = client.get(f"/api/queries/{query_id}/explain", headers=headers).json()["data"]
    assert explain["optimized_plan"] is not None
    assert len(explain["optimizer_trace"]) > 0
    assert any(t["rule"] == "projection_pruning" for t in explain["optimizer_trace"])
    assert len(explain["block_pruning"]) > 0
    skipped = [p for p in explain["block_pruning"] if p["column"] == "id" and p["state"] in {"skipped", "metadata_check"}]
    assert len(skipped) >= 1


def test_query_prune_impossible_eq(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    dataset_id, table_id = _import_sample(client, headers)

    resp = client.post(
        "/api/queries",
        headers=headers,
        json={
            "dataset_id": dataset_id,
            "table_id": table_id,
            "sql": "SELECT id FROM data WHERE id = 999999",
        },
    )
    explain = client.get(f"/api/queries/{resp.json()['data']['query_id']}/explain", headers=headers).json()["data"]
    id_blocks = [p for p in explain["block_pruning"] if p["column"] == "id"]
    assert all(p["verdict"] == "always_false" for p in id_blocks)
