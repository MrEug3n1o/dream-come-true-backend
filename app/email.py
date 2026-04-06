import logging
import resend
from app.config import get_email_settings, get_settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, html_body: str) -> None:
    """Send email via Resend API (works on Render — no SMTP ports needed)."""
    settings = get_email_settings()

    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s: %s", to_email, subject)
        return

    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": to_email,
            "subject": subject,
            "html": html_body,
        })
        logger.info("Email sent to %s: %s", to_email, subject)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        raise


def send_reset_email(to_email: str, reset_token: str, full_name: str) -> None:
    """Send a password reset link."""
    email_settings = get_email_settings()
    app_settings = get_settings()

    reset_url = f"{app_settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html = f"""
    <html><body>
      <h2>Hello, {full_name}!</h2>
      <p>We received a request to reset your Dream Maker password.</p>
      <p>
        <a href="{reset_url}" style="
          background:#c9a84c;color:#fff;padding:12px 24px;
          border-radius:6px;text-decoration:none;font-weight:bold;
        ">Reset My Password</a>
      </p>
      <p>This link expires in {email_settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
      <p>If you didn't request this, you can safely ignore this email.</p>
      <hr/><small>Dream Maker</small>
    </body></html>
    """
    _send(to_email, "Reset your Dream Maker password", html)


def send_dream_completed_email(
    to_email: str,
    owner_name: str,
    dream_title: str,
    donor_name: str,
) -> None:
    """Notify dream owner that their dream has been fulfilled."""
    html = f"""
    <html><body>
      <h2>Your dream came true, {owner_name}!</h2>
      <p>
        We have wonderful news — <strong>{donor_name}</strong> has just fulfilled
        your dream: <strong>"{dream_title}"</strong>.
      </p>
      <p>Thank you for sharing your dream with the world.</p>
      <hr/><small>Dream Maker — making dreams come true 🌟</small>
    </body></html>
    """
    _send(to_email, f'Your dream "{dream_title}" has been fulfilled! 🎉', html)
