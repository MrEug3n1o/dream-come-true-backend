import pytest
from fastapi.testclient import TestClient
from tests.conftest import auth_headers


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alice@test.com"
        assert data["role"] == "user"          # always user on self-register
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client):
        payload = {"full_name": "Alice", "email": "alice@test.com", "password": "pass123"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Bob", "email": "bob@test.com", "password": "abc"
        })
        assert resp.status_code == 422

    def test_register_missing_email(self, client):
        resp = client.post("/auth/register", json={"full_name": "Bob", "password": "pass123"})
        assert resp.status_code == 422

    def test_register_role_always_user(self, client):
        """Even if someone tries to pass role in the body it's ignored (field not in schema)."""
        resp = client.post("/auth/register", json={
            "full_name": "Hacker", "email": "hack@test.com", "password": "pass123", "role": "admin"
        })
        # Either 201 (extra field ignored) or 422 (strict schema) — never admin
        if resp.status_code == 201:
            assert resp.json()["role"] == "user"


class TestLogin:
    def test_login_success(self, client):
        client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "pass123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", json={"email": "nobody@test.com", "password": "pass"})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={"email": "only@test.com"})
        assert resp.status_code == 422


class TestGetMe:
    def test_get_me_authenticated(self, client, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"

    def test_get_me_no_token(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_get_me_invalid_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401
