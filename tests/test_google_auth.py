"""
Tests for Google OAuth flow.
All Google HTTP calls are mocked — no real Google account needed.
"""
from unittest.mock import patch, AsyncMock, MagicMock
import pytest


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
    def test_google_login_redirects(self, client):
        """GET /auth/google should redirect to Google consent screen."""
        resp = client.get("/auth/google", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "accounts.google.com" in resp.headers["location"]

    def test_google_login_includes_required_params(self, client):
        resp = client.get("/auth/google", follow_redirects=False)
        location = resp.headers["location"]
        assert "response_type=code" in location
        assert "scope=" in location
        assert "redirect_uri=" in location


class TestGoogleCallback:
    @patch("app.routers.google_auth.httpx.AsyncClient")
    async def test_new_user_created_on_first_login(self, mock_client_cls, client, db):
        """First Google login creates a new user automatically."""
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

    @patch("app.routers.google_auth.httpx.AsyncClient")
    async def test_existing_user_logs_in(self, mock_client_cls, client, regular_user, db):
        """If email already exists, no duplicate is created."""
        from app.models.models import User

        # Change regular_user email to match Google
        regular_user.email = "googleuser@gmail.com"
        db.commit()

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(200, GOOGLE_USER_INFO)

        client.get("/auth/google/callback?code=testcode", follow_redirects=False)

        count = db.query(User).filter(User.email == "googleuser@gmail.com").count()
        assert count == 1  # no duplicate

    @patch("app.routers.google_auth.httpx.AsyncClient")
    async def test_sets_auth_cookie(self, mock_client_cls, client):
        """Callback must set the access_token cookie."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(200, GOOGLE_USER_INFO)

        resp = client.get("/auth/google/callback?code=testcode", follow_redirects=False)
        assert "access_token" in resp.cookies

    @patch("app.routers.google_auth.httpx.AsyncClient")
    async def test_google_token_exchange_failure(self, mock_client_cls, client):
        """If Google rejects the code, return 400."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(400, {"error": "invalid_grant"})

        resp = client.get("/auth/google/callback?code=badcode", follow_redirects=False)
        assert resp.status_code == 400

    @patch("app.routers.google_auth.httpx.AsyncClient")
    async def test_google_userinfo_failure(self, mock_client_cls, client):
        """If fetching user info fails, return 400."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = make_mock_response(200, {"access_token": "gtoken"})
        mock_client.get.return_value = make_mock_response(401, {"error": "unauthorized"})

        resp = client.get("/auth/google/callback?code=testcode", follow_redirects=False)
        assert resp.status_code == 400

    def test_callback_requires_code_param(self, client):
        """Calling callback without ?code= should fail."""
        resp = client.get("/auth/google/callback", follow_redirects=False)
        assert resp.status_code == 422
