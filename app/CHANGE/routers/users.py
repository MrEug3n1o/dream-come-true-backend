from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.CHANGE.models import User
from app.CHANGE.schemas import UserOut, DreamOut
from app.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return current_user


@router.get("/me/dreams", response_model=list[DreamOut])
def get_my_dreams(
    current_user: User = Depends(get_current_user),
):
    """Get all dreams submitted by the current user (if they are a dreamer)."""
    return current_user.dreams
