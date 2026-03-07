from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dream, User
from app.models.schemas import UserOut, DreamOut
from app.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the current user's profile."""
    return current_user


@router.get("/me/dreams", response_model=list[DreamOut])
def get_my_dreams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all dreams owned by the current user."""
    return db.query(Dream).filter(Dream.owner_id == current_user.user_id).all()
