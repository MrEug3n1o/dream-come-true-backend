"""
Tests for Stripe payment flow.
All Stripe API calls are mocked — no real Stripe account needed.
"""
import json
from unittest.mock import patch, MagicMock
from tests.conftest import login


MOCK_STRIPE_SETTINGS = MagicMock()
MOCK_STRIPE_SETTINGS.STRIPE_SECRET_KEY = "sk_test_fake"
MOCK_STRIPE_SETTINGS.STRIPE_WEBHOOK_SECRET = "whsec_fake"


def make_checkout_session(session_id="cs_test_123", url="https://checkout.stripe.com/pay/cs_test_123"):
    mock = MagicMock()
    mock.id = session_id
    mock.url = url
    mock.payment_status = "paid"
    return mock


def make_webhook_event(dream_id: str, donor_id: str, payment_status: str = "paid"):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "payment_status": payment_status,
                "metadata": {
                    "dream_id": dream_id,
                    "donor_id": donor_id,
                    "donor_email": "donor@test.com",
                },
            }
        },
    }


class TestCreateCheckoutSession:
    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_create_session_success(self, mock_stripe, mock_settings, client, regular_user, sample_dream):
        mock_stripe.checkout.Session.create.return_value = make_checkout_session()
        mock_stripe.error.StripeError = Exception

        login(client, "user@test.com", "user1234")
        # use another_user to pay (can't pay own dream)
        # create second user and login as them
        client.post("/auth/register", json={
            "full_name": "Donor", "email": "donor2@test.com", "password": "donor123"
        })
        login(client, "donor2@test.com", "donor123")

        resp = client.post(f"/payments/dreams/{sample_dream.dream_id}/checkout")
        assert resp.status_code == 201
        data = resp.json()
        assert "checkout_url" in data
        assert "session_id" in data
        assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_requires_auth(self, mock_stripe, mock_settings, client, sample_dream):
        resp = client.post(f"/payments/dreams/{sample_dream.dream_id}/checkout")
        assert resp.status_code == 401

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_cannot_pay_own_dream(self, mock_stripe, mock_settings, client, regular_user, sample_dream):
        mock_stripe.error.StripeError = Exception
        login(client, "user@test.com", "user1234")
        resp = client.post(f"/payments/dreams/{sample_dream.dream_id}/checkout")
        assert resp.status_code == 400
        assert "own dream" in resp.json()["detail"]

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_cannot_pay_completed_dream(self, mock_stripe, mock_settings, client, another_user, completed_dream):
        mock_stripe.error.StripeError = Exception
        login(client, "another@test.com", "another123")
        resp = client.post(f"/payments/dreams/{completed_dream.dream_id}/checkout")
        assert resp.status_code == 409

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_dream_not_found(self, mock_stripe, mock_settings, client, regular_user):
        mock_stripe.error.StripeError = Exception
        login(client, "user@test.com", "user1234")
        resp = client.post("/payments/dreams/nonexistent/checkout")
        assert resp.status_code == 404

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_stripe_error_returns_503(self, mock_stripe, mock_settings, client, another_user, sample_dream):
        mock_stripe.error.StripeError = Exception
        mock_stripe.checkout.Session.create.side_effect = Exception("Stripe down")
        login(client, "another@test.com", "another123")
        resp = client.post(f"/payments/dreams/{sample_dream.dream_id}/checkout")
        assert resp.status_code == 503


class TestStripeWebhook:
    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.send_dream_completed_email")
    @patch("app.routers.payments.stripe")
    def test_webhook_completes_dream(self, mock_stripe, mock_email, mock_settings,
                                     client, regular_user, another_user, sample_dream, db):
        mock_stripe.error.SignatureVerificationError = Exception
        mock_stripe.Webhook.construct_event.return_value = make_webhook_event(
            dream_id=sample_dream.dream_id,
            donor_id=another_user.user_id,
        )

        resp = client.post(
            "/payments/webhook",
            content=b"fake_payload",
            headers={"stripe-signature": "fake_sig"},
        )
        assert resp.status_code == 200

        db.expire_all()
        from app.models.models import Dream
        updated = db.query(Dream).filter(Dream.dream_id == sample_dream.dream_id).first()
        assert updated.is_completed is True

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.send_dream_completed_email")
    @patch("app.routers.payments.stripe")
    def test_webhook_sends_email_to_owner(self, mock_stripe, mock_email, mock_settings,
                                          client, regular_user, another_user, sample_dream):
        mock_stripe.error.SignatureVerificationError = Exception
        mock_stripe.Webhook.construct_event.return_value = make_webhook_event(
            dream_id=sample_dream.dream_id,
            donor_id=another_user.user_id,
        )

        client.post(
            "/payments/webhook",
            content=b"fake_payload",
            headers={"stripe-signature": "fake_sig"},
        )

        mock_email.assert_called_once()
        call_kwargs = mock_email.call_args.kwargs
        assert call_kwargs["to_email"] == regular_user.email
        assert call_kwargs["dream_title"] == sample_dream.title

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_webhook_invalid_signature(self, mock_stripe, mock_settings, client):
        mock_stripe.error.SignatureVerificationError = Exception
        mock_stripe.Webhook.construct_event.side_effect = Exception("bad sig")

        resp = client.post(
            "/payments/webhook",
            content=b"fake_payload",
            headers={"stripe-signature": "bad_sig"},
        )
        assert resp.status_code == 400

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_webhook_ignores_unpaid_session(self, mock_stripe, mock_settings,
                                            client, regular_user, another_user, sample_dream, db):
        mock_stripe.error.SignatureVerificationError = Exception
        mock_stripe.Webhook.construct_event.return_value = make_webhook_event(
            dream_id=sample_dream.dream_id,
            donor_id=another_user.user_id,
            payment_status="unpaid",
        )

        client.post(
            "/payments/webhook",
            content=b"fake_payload",
            headers={"stripe-signature": "fake_sig"},
        )

        db.expire_all()
        from app.models.models import Dream
        dream = db.query(Dream).filter(Dream.dream_id == sample_dream.dream_id).first()
        assert dream.is_completed is False

    @patch("app.routers.payments.get_stripe_settings", return_value=MOCK_STRIPE_SETTINGS)
    @patch("app.routers.payments.stripe")
    def test_webhook_already_completed_dream(self, mock_stripe, mock_settings,
                                             client, regular_user, another_user, completed_dream):
        mock_stripe.error.SignatureVerificationError = Exception
        mock_stripe.Webhook.construct_event.return_value = make_webhook_event(
            dream_id=completed_dream.dream_id,
            donor_id=another_user.user_id,
        )

        resp = client.post(
            "/payments/webhook",
            content=b"fake_payload",
            headers={"stripe-signature": "fake_sig"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_completed"
