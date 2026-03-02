"""Tests for /auth/register, /auth/login, /auth/me"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import auth_headers


class TestRegister:
    def test_register_donor_success(self, client: TestClient):
        resp = client.post("/auth/register", json={
            "full_name": "Jane Doe",
            "email": "jane@test.com",
            "password": "secret123",
            "role": "donor",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "jane@test.com"
        assert data["role"] == "donor"
        assert data["full_name"] == "Jane Doe"
        assert "user_id" in data
        assert "password_hash" not in data  # never expose hash

    def test_register_dreamer_with_person_type(self, client: TestClient):
        resp = client.post("/auth/register", json={
            "full_name": "Sofia",
            "email": "sofia@test.com",
            "password": "dream123",
            "role": "dreamer",
            "person_type": "child",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "dreamer"
        assert data["person_type"] == "child"

    def test_register_all_person_types(self, client: TestClient):
        for i, ptype in enumerate(["veteran", "elderly", "child", "animal_shelter", "other"]):
            resp = client.post("/auth/register", json={
                "full_name": f"User {i}",
                "email": f"user{i}@test.com",
                "password": "pass123",
                "role": "dreamer",
                "person_type": ptype,
            })
            assert resp.status_code == 201
            assert resp.json()["person_type"] == ptype

    def test_register_duplicate_email(self, client: TestClient, donor_user):
        resp = client.post("/auth/register", json={
            "full_name": "Another User",
            "email": donor_user.email,
            "password": "pass123",
        })
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_register_short_password(self, client: TestClient):
        resp = client.post("/auth/register", json={
            "full_name": "User",
            "email": "short@test.com",
            "password": "ab",
        })
        assert resp.status_code == 422

    def test_register_missing_email(self, client: TestClient):
        resp = client.post("/auth/register", json={
            "full_name": "User",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_register_invalid_role(self, client: TestClient):
        resp = client.post("/auth/register", json={
            "full_name": "User",
            "email": "bad@test.com",
            "password": "pass123",
            "role": "superuser",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success_returns_token(self, client: TestClient, donor_user):
        resp = client.post("/auth/login", data={
            "username": donor_user.email,
            "password": "donor123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_login_wrong_password(self, client: TestClient, donor_user):
        resp = client.post("/auth/login", data={
            "username": donor_user.email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client: TestClient):
        resp = client.post("/auth/login", data={
            "username": "nobody@test.com",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client: TestClient):
        resp = client.post("/auth/login", data={"username": "only@test.com"})
        assert resp.status_code == 422


class TestGetMe:
    def test_get_me_authenticated(self, client: TestClient, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == donor_user.email
        assert data["user_id"] == donor_user.user_id

    def test_get_me_no_token(self, client: TestClient):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer fake.token.here"})
        assert resp.status_code == 401
