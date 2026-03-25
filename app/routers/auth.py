from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserRole
from app.models.schemas import UserLogin, UserRegister, UserOut, Token, MessageResponse
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, COOKIE_NAME, COOKIE_MAX_AGE
)
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Auth"])

IS_PROD = settings.APP_ENV == "production"


def set_auth_cookie(response: Response, token: str):
    """
    Production:  SameSite=None; Secure=True  — required for cross-origin (frontend on different domain)
    Development: SameSite=Lax;  Secure=False — works over HTTP for local testing and pytest
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite="none" if IS_PROD else "lax",
        max_age=COOKIE_MAX_AGE,
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=IS_PROD,
        samesite="none" if IS_PROD else "lax",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. Role is always 'user' — admins are promoted manually."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login and set HttpOnly cookie with JWT."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({"sub": user.user_id})
    set_auth_cookie(response, token)
    return {"token_type": "bearer", "user_role": user.role}


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Clear the auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
