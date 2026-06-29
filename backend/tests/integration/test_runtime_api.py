from __future__ import annotations


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "runtime_user", "email": "runtime@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "runtime_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_runtime_api(client):
    headers = _auth_headers(client)
    resp = client.get("/api/runtime", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["engine_version"] == "0.1"
    assert data["memory_total_bytes"] > 0
    assert 0 <= data["memory_used_bytes"] <= data["memory_total_bytes"]
    assert data["process_rss_bytes"] > 0
