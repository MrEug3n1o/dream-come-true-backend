from tests.conftest import login


class TestAdminUserManagement:
    def test_list_users(self, client, admin_user, regular_user):
        login(client, "admin@test.com", "admin123")
        resp = client.get("/admin/users")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_users_filter_by_role(self, client, admin_user, regular_user):
        login(client, "admin@test.com", "admin123")
        resp = client.get("/admin/users?role=user")
        assert all(u["role"] == "user" for u in resp.json())

    def test_get_user_by_id(self, client, admin_user, regular_user):
        login(client, "admin@test.com", "admin123")
        resp = client.get(f"/admin/users/{regular_user.user_id}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"

    def test_get_user_not_found(self, client, admin_user):
        login(client, "admin@test.com", "admin123")
        assert client.get("/admin/users/bad-id").status_code == 404

    def test_promote_user_to_admin(self, client, admin_user, regular_user):
        login(client, "admin@test.com", "admin123")
        resp = client.patch(f"/admin/users/{regular_user.user_id}/role?role=admin")
        assert resp.json()["role"] == "admin"

    def test_demote_admin_to_user(self, client, admin_user, regular_user):
        login(client, "admin@test.com", "admin123")
        client.patch(f"/admin/users/{regular_user.user_id}/role?role=admin")
        resp = client.patch(f"/admin/users/{regular_user.user_id}/role?role=user")
        assert resp.json()["role"] == "user"

    def test_cannot_change_own_role(self, client, admin_user):
        login(client, "admin@test.com", "admin123")
        assert client.patch(f"/admin/users/{admin_user.user_id}/role?role=user").status_code == 400

    def test_list_users_requires_admin(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.get("/admin/users").status_code == 403

    def test_list_users_requires_auth(self, client):
        assert client.get("/admin/users").status_code == 401

    def test_pagination(self, client, admin_user, regular_user, another_user):
        login(client, "admin@test.com", "admin123")
        assert len(client.get("/admin/users?skip=0&limit=2").json()) == 2
