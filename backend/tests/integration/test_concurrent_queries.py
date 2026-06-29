from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "conc_user", "email": "conc@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "conc_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wait_job(client, headers, job_id: int) -> dict:
    for _ in range(150):
        body = client.get(f"/api/import-jobs/{job_id}", headers=headers).json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("import timeout")


def test_concurrent_read_queries_complete(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    with (SAMPLES / "basic.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("basic.csv", fh, "text/csv")},
            data={"table_name": "data", "import_mode": "strict", "target_block_bytes": "512"},
        )
    data = resp.json()["data"]
    assert _wait_job(client, headers, data["job_id"])["status"] == "completed"
    tables = client.get(f"/api/datasets/{data['dataset_id']}/tables", headers=headers).json()["data"]
    table_id = tables[0]["id"]
    dataset_id = data["dataset_id"]

    def submit_one(sql: str) -> str:
        q = client.post(
            "/api/queries",
            headers=headers,
            json={"dataset_id": dataset_id, "table_id": table_id, "sql": sql},
        ).json()["data"]["query_id"]
        for _ in range(100):
            st = client.get(f"/api/queries/{q}", headers=headers).json()["data"]["status"]
            if st in {"completed", "failed", "cancelled"}:
                return st
            time.sleep(0.1)
        return "timeout"

    sqls = [
        "SELECT id FROM data WHERE id > 0",
        "SELECT COUNT(*) AS c FROM data",
        "SELECT id FROM data WHERE id < 10",
        "SELECT id FROM data LIMIT 3",
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(submit_one, sqls))
    assert results == ["completed"] * 4
