import os

os.environ["DATABASE_URL"] = "sqlite:///./test_lumen.db"

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app, get_llm  # noqa: E402

app.dependency_overrides[get_llm] = lambda: (lambda history: f"echo: {history[-1]['content']}")
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    if os.path.exists("test_lumen.db"):
        os.remove("test_lumen.db")


def signup(email, password="password123"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_register_login_me_and_duplicate():
    headers = signup("a@example.com")
    assert client.get("/auth/me", headers=headers).json()["email"] == "a@example.com"
    assert client.post("/auth/register", json={"email": "A@example.com", "password": "password123"}).status_code == 409
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "password123"}).status_code == 200
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "wrongpass1"}).status_code == 401
    assert client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"}).status_code == 401


def test_validation():
    assert client.post("/auth/register", json={"email": "bad", "password": "password123"}).status_code == 422
    assert client.post("/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 422


def test_password_is_hashed():
    from app.db import SessionLocal
    from app.models import User

    signup("hash@example.com")
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="hash@example.com").one()
        assert u.password_hash.startswith("$2") and "password123" not in u.password_hash


def test_protected_routes_need_valid_token():
    assert client.get("/conversations").status_code == 401
    assert client.post("/chat", json={"message": "hi"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    expired = jwt.encode({"sub": "1", "exp": 1}, settings.secret_key, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_chat_flow_and_memory():
    h = signup("chat@example.com")
    r = client.post("/chat", json={"message": "hello there"}, headers=h)
    assert r.status_code == 200
    cid = r.json()["conversation"]["id"]
    assert r.json()["reply"]["content"] == "echo: hello there"
    client.post("/chat", json={"message": "second", "conversation_id": cid}, headers=h)
    detail = client.get(f"/conversations/{cid}", headers=h).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert [c["id"] for c in client.get("/conversations", headers=h).json()] == [cid]
    assert client.delete(f"/conversations/{cid}", headers=h).status_code == 204
    assert client.get(f"/conversations/{cid}", headers=h).status_code == 404


def test_users_cannot_see_each_others_conversations():
    alice, bob = signup("alice@example.com"), signup("bob@example.com")
    cid = client.post("/chat", json={"message": "secret"}, headers=alice).json()["conversation"]["id"]
    assert client.get(f"/conversations/{cid}", headers=bob).status_code == 404
    assert client.delete(f"/conversations/{cid}", headers=bob).status_code == 404
    assert client.post("/chat", json={"message": "x", "conversation_id": cid}, headers=bob).status_code == 404
    assert client.get("/conversations", headers=bob).json() == []


def test_llm_failure_returns_502_and_saves_nothing():
    from app import llm as llm_mod

    def boom(history):
        raise llm_mod.LLMError("down")

    h = signup("err@example.com")
    app.dependency_overrides[get_llm] = lambda: boom
    assert client.post("/chat", json={"message": "hi"}, headers=h).status_code == 502
    app.dependency_overrides[get_llm] = lambda: (lambda history: "ok")
    assert client.get("/conversations", headers=h).json() == []
