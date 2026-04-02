"""
Tests for Google OAuth flow.
All Google HTTP calls and settings are mocked — no real Google account needed.
"""
from unittest.mock import patch, AsyncMock, MagicMock


MOCK_GOOGLE_SETTINGS = MagicMock()
MOCK_GOOGLE_SETTINGS.GOOGLE_CLIENT_ID = "test-client-id"
MOCK_GOOGLE_SETTINGS.GOOGLE_CLIENT_SECRET = "test-client-secret"
MOCK_GOOGLE_SETTINGS.GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"

GOOGLE_USER_INFO = {
    "email": "googleuser@gmail.com",
    "name": "Google User",
    "sub": "google-uid-123",
}


def make_mock_response(status_code: int, json_data: dict):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


class TestGoogleLogin:
    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    def test_google_login_redirects(self, mock_settings, client):
        resp = client.get("/auth/google", follow_redirects=False)
        assert resp.status_code in (302, 307)

    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    def test_google_login_includes_required_params(self, mock_settings, client):
        resp = client.get("/auth/google", follow_redirects=False)
        location = resp.headers["location"]
        assert "accounts.google.com" in location
        assert "response_type=code" in location
        assert "redirect_uri=" in location
        assert "test-client-id" in location


class TestGoogleCallback:
    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    @patch("app.routers.google_auth.httpx.AsyncClient")
    def test_new_user_created_on_first_login(self, mock_client_cls, mock_settings, client, db):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(200, GOOGLE_USER_INFO)

        resp = client.get("/auth/google/callback?code=testcode", follow_redirects=False)
        assert resp.status_code in (302, 307)

        from app.models.models import User
        user = db.query(User).filter(User.email == "googleuser@gmail.com").first()
        assert user is not None
        assert user.full_name == "Google User"
        assert user.role.value == "user"

    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    @patch("app.routers.google_auth.httpx.AsyncClient")
    def test_existing_user_no_duplicate(self, mock_client_cls, mock_settings, client, regular_user, db):
        regular_user.email = "googleuser@gmail.com"
        db.commit()

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(200, GOOGLE_USER_INFO)

        client.get("/auth/google/callback?code=testcode", follow_redirects=False)

        from app.models.models import User
        count = db.query(User).filter(User.email == "googleuser@gmail.com").count()
        assert count == 1

    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    @patch("app.routers.google_auth.httpx.AsyncClient")
    def test_sets_auth_cookie(self, mock_client_cls, mock_settings, client):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(200, GOOGLE_USER_INFO)

        resp = client.get("/auth/google/callback?code=testcode", follow_redirects=False)
        assert "access_token" in resp.cookies

    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    @patch("app.routers.google_auth.httpx.AsyncClient")
    def test_google_token_exchange_failure(self, mock_client_cls, mock_settings, client):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(400, {"error": "invalid_grant"})

        resp = client.get("/auth/google/callback?code=badcode", follow_redirects=False)
        assert resp.status_code == 400

    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    @patch("app.routers.google_auth.httpx.AsyncClient")
    def test_google_userinfo_failure(self, mock_client_cls, mock_settings, client):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(401, {"error": "unauthorized"})

        resp = client.get("/auth/google/callback?code=testcode", follow_redirects=False)
        assert resp.status_code == 400

    @patch("app.routers.google_auth.get_google_settings", return_value=MOCK_GOOGLE_SETTINGS)
    def test_callback_requires_code_param(self, mock_settings, client):
        resp = client.get("/auth/google/callback", follow_redirects=False)
        assert resp.status_code == 422
