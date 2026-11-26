import pytest
from starlette.websockets import WebSocketDisconnect


def register_and_login(client, username):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": "Correct123"},
    )
    client.post(
        "/api/auth/login",
        json={"username": username, "password": "Correct123"},
    )


def test_private_history_is_scoped_to_authenticated_participants(client):
    register_and_login(client, "alice")
    alice = client.get("/api/auth/me").json()["data"]["id"]
    client.post("/api/auth/logout")
    register_and_login(client, "bob")
    bob = client.get("/api/auth/me").json()["data"]["id"]

    with client.websocket_connect("/ws/chat") as socket:
        socket.send_json(
            {
                "type": "privateMessage",
                "requestId": "fd5afc1a-6969-44da-95cf-41c8b8a8d01d",
                "payload": {"receiverId": alice, "senderId": 999, "content": "hello"},
            }
        )
        accepted = socket.receive_json()
        assert accepted["type"] == "messageAccepted"

    history = client.get("/api/messages/private/1")
    assert history.status_code == 200
    assert history.json()["data"]["items"][0]["content"] == "hello"
    assert history.json()["data"]["items"][0]["senderId"] == bob


def test_private_history_requires_authentication(client):
    response = client.get("/api/messages/private/1")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_websocket_requires_authentication(client):
    with pytest.raises(WebSocketDisconnect) as disconnect:
        with client.websocket_connect("/ws/chat"):
            pass
    assert disconnect.value.code == 4401
