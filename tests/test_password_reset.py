"""
Tests for the password reset flow.
Email sending is mocked so no SMTP server is needed.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models.models import PasswordResetToken
from tests.conftest import auth_headers


# ─── Helper ───────────────────────────────────────────────────────────────────

def request_reset(client, email: str):
    """POST /auth/forgot-password and return response."""
    return client.post("/auth/forgot-password", json={"email": email})


def do_reset(client, token: str, new_password: str):
    """POST /auth/reset-password and return response."""
    return client.post("/auth/reset-password", json={"token": token, "new_password": new_password})


def get_reset_token(db, user_id: str) -> PasswordResetToken:
    """Fetch the latest unused token for a user from the test DB."""
    return (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used == False)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestForgotPassword:
    @patch("app.routers.password_reset.send_reset_email")
    def test_known_email_creates_token(self, mock_send, client, regular_user, db):
        resp = request_reset(client, "user@test.com")
        assert resp.status_code == 200
        assert "reset link has been sent" in resp.json()["message"]
        token = get_reset_token(db, regular_user.user_id)
        assert token is not None
        assert token.used is False

    @patch("app.routers.password_reset.send_reset_email")
    def test_known_email_calls_send_email(self, mock_send, client, regular_user):
        request_reset(client, "user@test.com")
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs.kwargs["to_email"] == "user@test.com"
        assert call_kwargs.kwargs["full_name"] == "Regular User"

    @patch("app.routers.password_reset.send_reset_email")
    def test_unknown_email_returns_same_message(self, mock_send, client):
        """Must not reveal whether email exists (prevents user enumeration)."""
        resp = request_reset(client, "ghost@test.com")
        assert resp.status_code == 200
        assert "reset link has been sent" in resp.json()["message"]
        mock_send.assert_not_called()

    @patch("app.routers.password_reset.send_reset_email")
    def test_second_request_invalidates_old_token(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        first_token = get_reset_token(db, regular_user.user_id)
        first_token_str = first_token.token

        request_reset(client, "user@test.com")

        # Old token should now be marked used
        db.expire_all()
        old = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == first_token_str
        ).first()
        assert old.used is True

        # New token should be active
        new_token = get_reset_token(db, regular_user.user_id)
        assert new_token.token != first_token_str

    def test_invalid_email_format(self, client):
        resp = client.post("/auth/forgot-password", json={"email": "not-an-email"})
        assert resp.status_code == 422


class TestResetPassword:
    @patch("app.routers.password_reset.send_reset_email")
    def test_successful_reset(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)

        resp = do_reset(client, token.token, "newpassword123")
        assert resp.status_code == 200
        assert "successfully" in resp.json()["message"]

    @patch("app.routers.password_reset.send_reset_email")
    def test_can_login_with_new_password(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)
        do_reset(client, token.token, "brandnew456")

        resp = client.post("/auth/login", json={"email": "user@test.com", "password": "brandnew456"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @patch("app.routers.password_reset.send_reset_email")
    def test_old_password_no_longer_works(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)
        do_reset(client, token.token, "brandnew456")

        resp = client.post("/auth/login", json={"email": "user@test.com", "password": "user1234"})
        assert resp.status_code == 401

    @patch("app.routers.password_reset.send_reset_email")
    def test_token_marked_used_after_reset(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)
        token_str = token.token

        do_reset(client, token_str, "newpassword123")

        db.expire_all()
        used_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token_str
        ).first()
        assert used_token.used is True

    @patch("app.routers.password_reset.send_reset_email")
    def test_token_cannot_be_reused(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)

        do_reset(client, token.token, "firstreset123")
        resp = do_reset(client, token.token, "secondreset456")
        assert resp.status_code == 400
        assert "already been used" in resp.json()["detail"]

    def test_invalid_token(self, client):
        resp = do_reset(client, "totally-fake-token", "newpassword123")
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]

    @patch("app.routers.password_reset.send_reset_email")
    def test_expired_token(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)

        # Manually expire the token
        token.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()

        resp = do_reset(client, token.token, "newpassword123")
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"]

    def test_short_new_password_rejected(self, client, regular_user):
        resp = do_reset(client, "sometoken", "abc")
        assert resp.status_code == 422

    def test_missing_token_field(self, client):
        resp = client.post("/auth/reset-password", json={"new_password": "newpassword123"})
        assert resp.status_code == 422
