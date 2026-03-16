"""
Email service for Dream Maker.
Sends password reset emails via SMTP.
Can be monkey-patched in tests via dependency injection.
"""
import smtplib
import logging
from fastapi import HTTPException, status
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_email_settings

logger = logging.getLogger(__name__)


def send_reset_email(to_email: str, reset_token: str, full_name: str) -> None:
    """
    Send a password reset email.
    Logs a warning and returns silently if SMTP is not configured
    (so the endpoint still works in dev without a mail server).
    """
    settings = get_email_settings()

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "SMTP not configured — skipping email send. "
            "Reset token for %s: %s", to_email, reset_token
        )
        return

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html_body = f"""
    <html><body>
      <h2>Hello, {full_name}!</h2>
      <p>We received a request to reset your Dream Maker password.</p>
      <p>
        <a href="{reset_url}" style="
          background:#c9a84c;color:#fff;padding:12px 24px;
          border-radius:6px;text-decoration:none;font-weight:bold;
        ">Reset My Password</a>
      </p>
      <p>This link expires in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
      <p>If you didn't request this, you can safely ignore this email.</p>
      <hr/>
      <small>Dream Maker — making dreams come true 🌟</small>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your Dream Maker password"
    msg["From"]    = settings.EMAIL_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
            logger.info("Reset email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send reset email. Please try again later."
        )
