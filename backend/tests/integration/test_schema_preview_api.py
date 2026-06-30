"""Schema preview API smoke test."""

from __future__ import annotations

from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "preview_user", "email": "preview@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "preview_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_schema_preview_csv(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    csv_path = SAMPLES / "basic.csv"
    with csv_path.open("rb") as fh:
        resp = client.post(
            "/api/datasets/schema-preview",
            headers=headers,
            files={"file": ("basic.csv", fh, "text/csv")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["row_sample_count"] == 5
    names = {c["name"] for c in body["columns"]}
    assert names == {"id", "name", "status", "qty", "flag"}
