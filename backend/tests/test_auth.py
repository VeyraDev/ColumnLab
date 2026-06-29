def test_register_login_profile(client):
    register_payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "secret12",
    }
    reg = client.post("/api/auth/register", json=register_payload)
    assert reg.status_code == 200
    reg_body = reg.json()
    assert reg_body["code"] == 0
    assert reg_body["data"]["username"] == "alice"
    token = reg_body["data"]["access_token"]
    assert token

    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret12"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["access_token"]

    profile = client.get(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    profile_body = profile.json()
    assert profile_body["data"]["username"] == "alice"
    assert profile_body["data"]["email"] == "alice@example.com"


def test_profile_requires_auth(client):
    response = client.get("/api/auth/profile")
    assert response.status_code == 401
    assert response.json()["code"] == 401


def test_duplicate_username(client):
    payload = {
        "username": "bob",
        "email": "bob@example.com",
        "password": "secret12",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 200
    dup = client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "bob2@example.com", "password": "secret12"},
    )
    assert dup.status_code == 400
