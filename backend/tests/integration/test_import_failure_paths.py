from __future__ import annotations

import json
import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "fail_user", "email": "fail@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "fail_user", "password": "secret12"})
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


def test_strict_import_failure_no_ready_dataset(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    with (SAMPLES / "strict_fail.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("strict_fail.csv", fh, "text/csv")},
            data={
                "import_mode": "strict",
                "target_block_bytes": "512",
                "schema_overrides": json.dumps([{"name": "id", "logical_type": "INT64"}]),
            },
        )
    job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert job["status"] == "failed"
    ds_id = resp.json()["data"]["dataset_id"]
    ds = client.get(f"/api/datasets/{ds_id}", headers=headers).json()["data"]
    assert ds["status"] != "ready"


def test_corrupted_csv_upload_fails(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    garbage = b"\xff\xfe not,a,valid\x00csv"
    resp = client.post(
        "/api/datasets/uploads",
        headers=headers,
        files={"file": ("broken.csv", garbage, "text/csv")},
        data={"import_mode": "strict", "target_block_bytes": "512"},
    )
    assert resp.status_code == 200
    job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert job["status"] == "failed"
