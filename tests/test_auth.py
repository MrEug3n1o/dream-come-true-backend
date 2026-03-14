from tests.conftest import login


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alice@test.com"
        assert data["role"] == "user"
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client):
        payload = {"full_name": "Alice", "email": "alice@test.com", "password": "pass123"}
        client.post("/auth/register", json=payload)
        assert client.post("/auth/register", json=payload).status_code == 409

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Bob", "email": "bob@test.com", "password": "abc"
        })
        assert resp.status_code == 422

    def test_register_missing_email(self, client):
        assert client.post("/auth/register", json={"full_name": "Bob", "password": "pass123"}).status_code == 422

    def test_register_always_creates_user_role(self, client):
        resp = client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        assert resp.json()["role"] == "user"


class TestLogin:
    def test_login_success_sets_cookie(self, client):
        client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "pass123"})
        assert resp.status_code == 200
        # Cookie should be set
        assert "access_token" in resp.cookies
        # Token must NOT be in the response body
        assert "access_token" not in resp.json()

    def test_login_returns_role(self, client):
        client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "pass123"})
        assert resp.json()["user_role"] == "user"

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        assert client.post("/auth/login", json={"email": "alice@test.com", "password": "wrong"}).status_code == 401

    def test_login_unknown_email(self, client):
        assert client.post("/auth/login", json={"email": "nobody@test.com", "password": "pass"}).status_code == 401

    def test_login_missing_fields(self, client):
        assert client.post("/auth/login", json={"email": "only@test.com"}).status_code == 422


class TestLogout:
    def test_logout_clears_cookie(self, client):
        client.post("/auth/register", json={
            "full_name": "Alice", "email": "alice@test.com", "password": "pass123"
        })
        login(client, "alice@test.com", "pass123")
        resp = client.post("/auth/logout")
        assert resp.status_code == 200
        # After logout, /me should return 401
        assert client.get("/auth/me").status_code == 401


class TestGetMe:
    def test_get_me_authenticated(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.get("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"

    def test_get_me_no_cookie(self, client):
        assert client.get("/auth/me").status_code == 401
