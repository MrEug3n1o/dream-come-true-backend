from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserRole
from app.models.schemas import UserOut
from app.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    skip:  int      = Query(0, ge=0),
    limit: int      = Query(50, ge=1, le=200),
    role:  UserRole = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """List all users with optional role filter. Admin only."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.offset(skip).limit(limit).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Get a specific user by ID. Admin only."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str,
    role: UserRole,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Promote or demote a user's role. Admin only. Cannot change own role."""
    if user_id == current_admin.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return user
