from __future__ import annotations

import time
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "disk_user", "email": "disk@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "disk_user", "password": "secret12"})
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


def test_disk_full_simulation_fails_import(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)

    import os

    original_replace = os.replace

    def boom_replace(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", boom_replace)

    with (SAMPLES / "basic.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("basic.csv", fh, "text/csv")},
            data={"table_name": "data", "import_mode": "strict", "target_block_bytes": "512"},
        )
    job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert job["status"] == "failed"
