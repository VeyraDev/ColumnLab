from __future__ import annotations

import time
import uuid
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"del_user_{suffix}"
    email = f"del_{suffix}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "secret12"},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wait_job(client, headers, job_id: int) -> dict:
    for _ in range(150):
        body = client.get(f"/api/import-jobs/{job_id}", headers=headers).json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("import timeout")


def _wait_tables(client, headers, dataset_id: int) -> list[dict]:
    for _ in range(50):
        tables = client.get(f"/api/datasets/{dataset_id}/tables", headers=headers).json()["data"]
        if tables:
            return tables
        time.sleep(0.2)
    raise AssertionError("dataset has no tables after import")


def test_delete_dataset_conflict_when_query_running(client, tmp_path, monkeypatch):
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
    job = _wait_job(client, headers, data["job_id"])
    assert job["status"] == "completed", job
    tables = _wait_tables(client, headers, data["dataset_id"])

    import app.engine.execution.executor as ex

    original_execute = ex.QueryExecutor.execute

    def slow_execute(self, physical, ctx):
        time.sleep(1.0)
        return original_execute(self, physical, ctx)

    monkeypatch.setattr(ex.QueryExecutor, "execute", slow_execute)

    client.post(
        "/api/queries",
        headers=headers,
        json={
            "dataset_id": data["dataset_id"],
            "table_id": tables[0]["id"],
            "sql": "SELECT id FROM data",
        },
    )

    delete_resp = client.delete(f"/api/datasets/{data['dataset_id']}", headers=headers)
    assert delete_resp.status_code == 409
    assert "活动查询" in delete_resp.json()["msg"]
