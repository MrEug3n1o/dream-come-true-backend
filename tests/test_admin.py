import pytest
from tests.conftest import auth_headers


class TestAdminUserManagement:
    def test_list_users(self, client, admin_user, regular_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.get("/admin/users", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_users_filter_by_role(self, client, admin_user, regular_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.get("/admin/users?role=user", headers=headers)
        assert resp.status_code == 200
        assert all(u["role"] == "user" for u in resp.json())

    def test_get_user_by_id(self, client, admin_user, regular_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.get(f"/admin/users/{regular_user.user_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"

    def test_get_user_not_found(self, client, admin_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        assert client.get("/admin/users/bad-id", headers=headers).status_code == 404

    def test_promote_user_to_admin(self, client, admin_user, regular_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.patch(
            f"/admin/users/{regular_user.user_id}/role?role=admin",
            headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_demote_admin_to_user(self, client, admin_user, regular_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        # First promote
        client.patch(f"/admin/users/{regular_user.user_id}/role?role=admin", headers=headers)
        # Then demote
        resp = client.patch(
            f"/admin/users/{regular_user.user_id}/role?role=user",
            headers=headers
        )
        assert resp.json()["role"] == "user"

    def test_cannot_change_own_role(self, client, admin_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.patch(
            f"/admin/users/{admin_user.user_id}/role?role=user",
            headers=headers
        )
        assert resp.status_code == 400

    def test_list_users_requires_admin(self, client, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        assert client.get("/admin/users", headers=headers).status_code == 403

    def test_list_users_requires_auth(self, client):
        assert client.get("/admin/users").status_code == 401

    def test_pagination(self, client, admin_user, regular_user, another_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.get("/admin/users?skip=0&limit=2", headers=headers)
        assert len(resp.json()) == 2
