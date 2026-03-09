import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_email_settings
from app.models.models import User, PasswordResetToken
from app.models.schemas import ForgotPasswordRequest, ResetPasswordRequest, MessageResponse
from app.auth import hash_password
from app.email import send_reset_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset link.
    Always returns the same message whether the email exists or not
    (prevents user enumeration).
    """
    settings = get_email_settings()
    SAFE_RESPONSE = {"message": "If that email is registered, a reset link has been sent."}

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return SAFE_RESPONSE

    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.user_id,
        PasswordResetToken.used == False,
    ).update({"used": True})

    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

    reset_token = PasswordResetToken(
        user_id=user.user_id,
        token=token_str,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()

    send_reset_email(
        to_email=user.email,
        reset_token=token_str,
        full_name=user.full_name,
    )

    return SAFE_RESPONSE


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Set a new password using a valid reset token.
    Token must be unused and not expired.
    """
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == payload.token)
        .first()
    )

    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if reset_token.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token has already been used")

    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired")

    user = db.query(User).filter(User.user_id == reset_token.user_id).first()
    user.password_hash = hash_password(payload.new_password)

    reset_token.used = True
    db.commit()

    return {"message": "Password has been reset successfully. You can now log in."}
