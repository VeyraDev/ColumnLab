from __future__ import annotations

import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "cancel_user", "email": "cancel@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "cancel_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wait_job(client, headers, job_id: int) -> dict:
    for _ in range(150):
        resp = client.get(f"/api/import-jobs/{job_id}", headers=headers)
        body = resp.json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("import timeout")


def test_query_cancel_sets_cancelled(client, tmp_path, monkeypatch):
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
    _wait_job(client, headers, data["job_id"])
    tables = client.get(f"/api/datasets/{data['dataset_id']}/tables", headers=headers).json()["data"]

    import app.engine.execution.executor as ex

    original_execute = ex.QueryExecutor.execute

    def slow_execute(self, physical, ctx):
        time.sleep(0.5)
        return original_execute(self, physical, ctx)

    monkeypatch.setattr(ex.QueryExecutor, "execute", slow_execute)

    submit = client.post(
        "/api/queries",
        headers=headers,
        json={
            "dataset_id": data["dataset_id"],
            "table_id": tables[0]["id"],
            "sql": "SELECT id FROM data",
        },
    )
    query_id = submit.json()["data"]["query_id"]
    client.post(f"/api/queries/{query_id}/cancel", headers=headers)

    deadline = time.time() + 10
    status = "running"
    while time.time() < deadline:
        st = client.get(f"/api/queries/{query_id}", headers=headers).json()["data"]
        status = st["status"]
        if status in {"cancelled", "completed", "failed"}:
            break
        time.sleep(0.1)
    assert status == "cancelled"
