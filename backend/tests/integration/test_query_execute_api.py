from __future__ import annotations

import json
import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "query_execute_golden.json"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "exec_user", "email": "exec@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "exec_user", "password": "secret12"})
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


def _wait_query(client, headers, query_id: int, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/queries/{query_id}", headers=headers)
        body = resp.json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("query did not finish")


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


def test_query_execute_and_result(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    dataset_id, table_id = _import_sample(client, headers)
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    for case in golden["queries"]:
        resp = client.post(
            "/api/queries",
            headers=headers,
            json={"dataset_id": dataset_id, "table_id": table_id, "sql": case["sql"]},
        )
        assert resp.status_code == 200
        query_id = resp.json()["data"]["query_id"]
        status = _wait_query(client, headers, query_id)
        assert status["status"] == "completed", status

        result = client.get(f"/api/queries/{query_id}/result", headers=headers).json()["data"]
        assert result["columns"] == case["columns"]
        assert result["rows"] == case["rows"]

        explain = client.get(f"/api/queries/{query_id}/explain", headers=headers).json()["data"]
        assert explain["physical_plan"] is not None
        assert explain["metrics"] is not None
        assert explain["metrics"]["scanned_blocks"] >= 0


def test_query_result_not_implemented(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    dataset_id, table_id = _import_sample(client, headers)
    resp = client.post(
        "/api/queries",
        headers=headers,
        json={"dataset_id": dataset_id, "table_id": table_id, "sql": "SELECT id FROM data LIMIT 1"},
    )
    query_id = resp.json()["data"]["query_id"]
    _wait_query(client, headers, query_id)
    result = client.get(f"/api/queries/{query_id}/result", headers=headers)
    assert result.status_code == 200
    assert result.json()["data"]["rows"]
