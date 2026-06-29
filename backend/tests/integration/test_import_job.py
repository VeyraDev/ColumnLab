from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "import_user", "email": "import@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "import_user", "password": "secret12"})
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


def test_import_csv_completed(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    csv_path = SAMPLES / "basic.csv"
    with csv_path.open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("basic.csv", fh, "text/csv")},
            data={"table_name": "data", "import_mode": "strict", "target_block_bytes": "512"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    job = _wait_job(client, headers, data["job_id"])
    assert job["status"] == "completed", job.get("error_message")
    assert job["rows_processed"] == 5

    ds = client.get(f"/api/datasets/{data['dataset_id']}", headers=headers).json()["data"]
    assert ds["status"] == "ready"
    assert ds["row_count"] == 5

    tables = client.get(f"/api/datasets/{data['dataset_id']}/tables", headers=headers).json()["data"]
    assert len(tables) == 1
    cols = client.get(f"/api/tables/{tables[0]['id']}/columns", headers=headers).json()["data"]
    assert len(cols) == 5
    smap = client.get(f"/api/tables/{tables[0]['id']}/storage-map", headers=headers).json()["data"]
    assert smap["column_count"] == 5


def test_import_strict_failure(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    with (SAMPLES / "strict_fail.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("strict_fail.csv", fh, "text/csv")},
            data={"import_mode": "strict", "target_block_bytes": "512", "schema_overrides": json.dumps([{"name": "id", "logical_type": "INT64"}])},
        )
    assert resp.status_code == 200
    job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert job["status"] == "failed"


def test_import_coerce_mode(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    with (SAMPLES / "coerce_sample.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("coerce_sample.csv", fh, "text/csv")},
            data={
                "import_mode": "coerce",
                "target_block_bytes": "512",
                "schema_overrides": json.dumps([{"name": "id", "logical_type": "INT64"}]),
            },
        )
    job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert job["status"] == "completed"
    assert job["error_count"] >= 1
