from __future__ import annotations

import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "block_user", "email": "block@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "block_user", "password": "secret12"})
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


def _import_sample(client, headers) -> tuple[int, list[dict]]:
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
    table_id = tables[0]["id"]
    columns = client.get(f"/api/tables/{table_id}/columns", headers=headers).json()["data"]
    return table_id, columns


def test_block_detail_and_preview(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    _, columns = _import_sample(client, headers)
    col = columns[0]
    col_id = col["id"]

    detail = client.get(f"/api/columns/{col_id}/blocks/0", headers=headers)
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["block_id"] == 0
    assert body["row_count"] > 0
    assert body["encoding"] in {"RAW", "RLE", "DICTIONARY"}

    preview = client.get(f"/api/columns/{col_id}/blocks/0/preview", headers=headers)
    assert preview.status_code == 200
    pdata = preview.json()["data"]
    assert pdata["winner_encoding"] in {"RAW", "RLE", "DICTIONARY"}
    assert len(pdata["candidates"]) >= 1
    assert any(c["selected"] for c in pdata["candidates"])
    assert pdata["block"]["row_count"] == body["row_count"]
