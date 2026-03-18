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
    """
    Login with email + password.
    Sets an HttpOnly cookie with SameSite=None so it works across
    different origins (e.g. frontend on localhost, backend on Render).
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({"sub": user.user_id})

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,      # JS cannot read this cookie
        secure=True,        # Must be True when SameSite=None — required by all browsers
        samesite="none",    # Allows cross-site requests (frontend and backend on different origins)
        max_age=COOKIE_MAX_AGE,
    )

    return {"token_type": "bearer", "user_role": user.role}


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
