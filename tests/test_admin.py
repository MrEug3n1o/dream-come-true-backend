"""Tests for /admin/* endpoints — dream CRUD, user management"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.models import User, Dream, UserRole, PersonType, ParticipationFormat
from app.auth import hash_password
from tests.conftest import auth_headers


class TestAdminCreateDream:
    def test_create_dream_as_admin(self, client: TestClient, admin_user, dreamer_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.post("/admin/dreams", json={
            "title": "New Dream",
            "description": "A wonderful dream",
            "participation_format": "online",
            "target_budget": 75.00,
            "dreamer_id": dreamer_user.user_id,
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Dream"
        assert data["dreamer_id"] == dreamer_user.user_id
        assert data["is_completed"] is False
        assert "dream_id" in data

    def test_create_dream_requires_admin(self, client: TestClient, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.post("/admin/dreams", json={
            "title": "Test", "description": "d",
            "participation_format": "online", "target_budget": 50,
        }, headers=headers)
        assert resp.status_code == 403

    def test_create_dream_requires_auth(self, client: TestClient):
        resp = client.post("/admin/dreams", json={
            "title": "Test", "description": "d",
            "participation_format": "online", "target_budget": 50,
        })
        assert resp.status_code == 401

    def test_create_dream_invalid_format(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.post("/admin/dreams", json={
            "title": "Test", "description": "d",
            "participation_format": "in-space", "target_budget": 50,
        }, headers=headers)
        assert resp.status_code == 422

    def test_create_dream_invalid_dreamer_id(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.post("/admin/dreams", json={
            "title": "Test", "description": "d",
            "participation_format": "online", "target_budget": 50,
            "dreamer_id": "nonexistent-uuid",
        }, headers=headers)
        assert resp.status_code == 404


class TestAdminUpdateDream:
    def test_update_dream_title(self, client: TestClient, admin_user, sample_dream):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.put(f"/admin/dreams/{sample_dream.dream_id}", json={
            "title": "Updated Title",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_dream_partial(self, client: TestClient, admin_user, sample_dream):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.put(f"/admin/dreams/{sample_dream.dream_id}", json={
            "target_budget": 999.99,
        }, headers=headers)
        assert resp.status_code == 200
        assert float(resp.json()["target_budget"]) == 999.99
        assert resp.json()["title"] == sample_dream.title  # unchanged

    def test_update_dream_not_found(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.put("/admin/dreams/no-such-id", json={"title": "x"}, headers=headers)
        assert resp.status_code == 404

    def test_update_dream_requires_admin(self, client: TestClient, donor_user, sample_dream):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.put(f"/admin/dreams/{sample_dream.dream_id}", json={"title": "x"}, headers=headers)
        assert resp.status_code == 403


class TestAdminDeleteDream:
    def test_delete_dream(self, client: TestClient, admin_user, sample_dream):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.delete(f"/admin/dreams/{sample_dream.dream_id}", headers=headers)
        assert resp.status_code == 204

        get_resp = client.get(f"/dreams/{sample_dream.dream_id}")
        assert get_resp.status_code == 404

    def test_delete_dream_not_found(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.delete("/admin/dreams/ghost-uuid", headers=headers)
        assert resp.status_code == 404

    def test_delete_requires_admin(self, client: TestClient, donor_user, sample_dream):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.delete(f"/admin/dreams/{sample_dream.dream_id}", headers=headers)
        assert resp.status_code == 403


class TestAdminCompleteDream:
    def test_mark_dream_completed(self, client: TestClient, admin_user, sample_dream):
        assert sample_dream.is_completed is False
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.patch(f"/admin/dreams/{sample_dream.dream_id}/complete", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_complete_not_found(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.patch("/admin/dreams/ghost/complete", headers=headers)
        assert resp.status_code == 404


class TestAdminUserManagement:
    def test_list_users(self, client: TestClient, admin_user, donor_user, dreamer_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.get("/admin/users", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3  # admin + donor + dreamer

    def test_list_users_filter_by_role(self, client: TestClient, admin_user, donor_user, dreamer_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.get("/admin/users?role=donor", headers=headers)
        assert resp.status_code == 200
        assert all(u["role"] == "donor" for u in resp.json())

    def test_get_user_by_id(self, client: TestClient, admin_user, donor_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.get(f"/admin/users/{donor_user.user_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == donor_user.email

    def test_get_user_not_found(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.get("/admin/users/nonexistent", headers=headers)
        assert resp.status_code == 404

    def test_update_user_role(self, client: TestClient, admin_user, donor_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.patch(
            f"/admin/users/{donor_user.user_id}/role?role=dreamer",
            headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "dreamer"

    def test_cannot_change_own_role(self, client: TestClient, admin_user):
        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.patch(
            f"/admin/users/{admin_user.user_id}/role?role=donor",
            headers=headers
        )
        assert resp.status_code == 400

    def test_list_users_requires_admin(self, client: TestClient, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.get("/admin/users", headers=headers)
        assert resp.status_code == 403

    def test_list_users_pagination(self, client: TestClient, admin_user, db: Session):
        for i in range(10):
            db.add(User(
                full_name=f"User {i}", email=f"u{i}@t.com",
                password_hash=hash_password("x"), role=UserRole.DONOR,
            ))
        db.commit()

        headers = auth_headers(client, admin_user.email, "admin123")
        resp = client.get("/admin/users?skip=0&limit=5", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 5
