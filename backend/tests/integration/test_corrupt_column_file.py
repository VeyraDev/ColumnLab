from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.engine.format.errors import CrcMismatchError
from app.engine.storage.reader import ColumnReader

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "corrupt_user", "email": "corrupt@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "corrupt_user", "password": "secret12"})
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


def _import_basic(client, headers) -> tuple[int, list[dict]]:
    with (SAMPLES / "basic.csv").open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": ("basic.csv", fh, "text/csv")},
            data={"table_name": "data", "import_mode": "strict", "target_block_bytes": "512"},
        )
    data = resp.json()["data"]
    job = _wait_job(client, headers, data["job_id"])
    assert job["status"] == "completed"
    tables = client.get(f"/api/datasets/{data['dataset_id']}/tables", headers=headers).json()["data"]
    columns = client.get(f"/api/tables/{tables[0]['id']}/columns", headers=headers).json()["data"]
    return data["dataset_id"], columns


def test_corrupt_column_payload_crc_detected(client, db_session, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    _, columns = _import_basic(client, headers)
    from app.catalog.models.catalog import Column

    col = db_session.get(Column, columns[0]["id"])
    assert col is not None
    col_path = Path(col.column_file_path)
    assert col_path.exists()
    reader = ColumnReader.open(col_path)
    entry = reader.index[0]
    from app.engine.format.headers import BlockHeader

    data = bytearray(col_path.read_bytes())
    header, after_header = BlockHeader.unpack(bytes(data), entry.offset)
    payload_start = after_header + header.stats_bytes
    data[payload_start] ^= 0xFF
    col_path.write_bytes(data)

    with pytest.raises(CrcMismatchError, match="CRC mismatch"):
        ColumnReader.open(col_path).read_block(0)

    col_id = columns[0]["id"]
    try:
        resp = client.get(f"/api/columns/{col_id}/blocks/0/preview", headers=headers)
        assert resp.status_code >= 400
        assert "CRC" in resp.text or "crc" in resp.text.lower()
    except Exception as exc:
        assert "CRC" in str(exc) or "crc" in str(exc).lower()
