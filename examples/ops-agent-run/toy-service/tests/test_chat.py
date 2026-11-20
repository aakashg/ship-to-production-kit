from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_healthz():
    assert client.get("/healthz").status_code == 200


def test_chat_ok():
    r = client.post("/v1/chat", json={"prompt": "hello", "max_tokens": 64})
    assert r.status_code == 200
