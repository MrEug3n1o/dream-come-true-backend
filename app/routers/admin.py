from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dream, User, UserRole
from app.models.schemas import DreamCreate, DreamUpdate, DreamOut, UserOut
from app.auth import get_current_admin, get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── Dream CRUD ──────────────────────────────────────────────────────────────

@router.post("/dreams", response_model=DreamOut, status_code=status.HTTP_201_CREATED)
def create_dream(
    payload: DreamCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Create a new dream entry. Admin only."""
    # dreamer_id can be explicitly set by admin, otherwise admin is the dreamer
    dreamer_id = payload.dreamer_id or current_admin.user_id
    if payload.dreamer_id:
        dreamer = db.query(User).filter(User.user_id == payload.dreamer_id).first()
        if not dreamer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dreamer user not found")

    dream = Dream(
        dreamer_id=dreamer_id,
        title=payload.title,
        description=payload.description,
        participation_format=payload.participation_format,
        target_budget=payload.target_budget,
    )
    db.add(dream)
    db.commit()
    db.refresh(dream)
    return dream


@router.put("/dreams/{dream_id}", response_model=DreamOut)
def update_dream(
    dream_id: str,
    payload: DreamUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Update a dream's details. Admin only."""
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dream, field, value)

    db.commit()
    db.refresh(dream)
    return dream


@router.delete("/dreams/{dream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dream(
    dream_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Permanently delete a dream. Admin only."""
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")
    db.delete(dream)
    db.commit()


@router.patch("/dreams/{dream_id}/complete", response_model=DreamOut)
def mark_dream_completed(
    dream_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Mark a dream as completed after confirming fulfillment. Admin only."""
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")
    dream.is_completed = True
    db.commit()
    db.refresh(dream)
    return dream


# ─── User Management ─────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserOut])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: UserRole = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """List all registered users with optional role filter. Admin only."""
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
    """Change a user's role. Admin only."""
    if user_id == current_admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role"
        )
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return user
