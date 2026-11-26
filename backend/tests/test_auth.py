def test_registration_login_cookie_and_logout(client):
    registered = client.post(
        "/api/auth/register",
        json={"username": "Alice_1", "password": "Correct123", "displayName": "Alice"},
    )
    assert registered.status_code == 201
    assert registered.json()["data"] == {
        "id": 1,
        "username": "alice_1",
        "displayName": "Alice",
        "role": "user",
    }

    login = client.post("/api/auth/login", json={"username": "ALICE_1", "password": "Correct123"})
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["data"]["username"] == "alice_1"

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_register_rejects_bad_password_and_duplicate_username(client):
    bad_password = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "onlyletters"},
    )
    assert bad_password.status_code == 400
    assert bad_password.json()["error"]["code"] == "VALIDATION_ERROR"

    payload = {"username": "alice", "password": "Correct123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    duplicate = client.post(
        "/api/auth/register",
        json={"username": "ALICE", "password": "Correct123"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "USERNAME_EXISTS"
