from datetime import datetime, timedelta
from unittest.mock import patch
from app.models.models import PasswordResetToken
from tests.conftest import login


def request_reset(client, email):
    return client.post("/auth/forgot-password", json={"email": email})

def do_reset(client, token, new_password):
    return client.post("/auth/reset-password", json={"token": token, "new_password": new_password})

def get_reset_token(db, user_id):
    return (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used == False)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )


class TestForgotPassword:
    @patch("app.routers.password_reset.send_reset_email")
    def test_known_email_creates_token(self, mock_send, client, regular_user, db):
        resp = request_reset(client, "user@test.com")
        assert resp.status_code == 200
        assert get_reset_token(db, regular_user.user_id) is not None

    @patch("app.routers.password_reset.send_reset_email")
    def test_unknown_email_same_response(self, mock_send, client):
        resp = request_reset(client, "ghost@test.com")
        assert resp.status_code == 200
        mock_send.assert_not_called()

    @patch("app.routers.password_reset.send_reset_email")
    def test_second_request_invalidates_old_token(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        first = get_reset_token(db, regular_user.user_id).token
        request_reset(client, "user@test.com")
        db.expire_all()
        old = db.query(PasswordResetToken).filter(PasswordResetToken.token == first).first()
        assert old.used is True


class TestResetPassword:
    @patch("app.routers.password_reset.send_reset_email")
    def test_successful_reset_and_login(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id).token
        assert do_reset(client, token, "newpassword123").status_code == 200
        # Can login with new password
        resp = client.post("/auth/login", json={"email": "user@test.com", "password": "newpassword123"})
        assert resp.status_code == 200
        assert "access_token" in resp.cookies

    @patch("app.routers.password_reset.send_reset_email")
    def test_old_password_no_longer_works(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id).token
        do_reset(client, token, "newpassword123")
        assert client.post("/auth/login", json={"email": "user@test.com", "password": "user1234"}).status_code == 401

    @patch("app.routers.password_reset.send_reset_email")
    def test_token_cannot_be_reused(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id).token
        do_reset(client, token, "first123")
        assert do_reset(client, token, "second456").status_code == 400

    def test_invalid_token(self, client):
        assert do_reset(client, "fake-token", "newpassword123").status_code == 400

    @patch("app.routers.password_reset.send_reset_email")
    def test_expired_token(self, mock_send, client, regular_user, db):
        request_reset(client, "user@test.com")
        token = get_reset_token(db, regular_user.user_id)
        token.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
        assert do_reset(client, token.token, "newpassword123").status_code == 400

    def test_short_password_rejected(self, client):
        assert do_reset(client, "sometoken", "abc").status_code == 422
