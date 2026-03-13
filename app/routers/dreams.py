import random
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dream, User, UserRole, PersonType, ParticipationFormat, DEFAULT_DREAM_IMAGE
from app.models.schemas import DreamCreate, DreamUpdate, DreamOut, DreamOutWithOwner
from app.auth import get_current_user, get_optional_user

router = APIRouter(prefix="/dreams", tags=["Dreams"])


def _get_dream_or_404(dream_id: str, db: Session) -> Dream:
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")
    return dream


def _require_ownership_or_admin(dream: Dream, current_user: User):
    if current_user.role != UserRole.ADMIN and dream.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own dreams"
        )


# ─── Public reads ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[DreamOut])
def list_dreams(
    participation_format: Optional[ParticipationFormat] = Query(None),
    person_type:          Optional[PersonType]           = Query(None),
    max_budget:           Optional[Decimal]              = Query(None),
    city:                 Optional[str]                  = Query(None, description="Filter by city"),
    is_completed:         Optional[bool]                 = Query(None),
    sort_by:              Optional[str]                  = Query(None, description="'date' or 'budget'"),
    db: Session = Depends(get_db),
):
    """List all dreams with optional filtering. Public endpoint."""
    query = db.query(Dream)

    if participation_format:
        query = query.filter(Dream.participation_format == participation_format)
    if person_type:
        query = query.filter(Dream.person_type == person_type)
    if max_budget is not None:
        query = query.filter(Dream.target_budget <= max_budget)
    if city:
        query = query.filter(Dream.city.ilike(f"%{city}%"))
    if is_completed is not None:
        query = query.filter(Dream.is_completed == is_completed)

    if sort_by == "budget":
        query = query.order_by(Dream.target_budget.asc())
    else:
        query = query.order_by(Dream.created_at.desc())

    return query.all()


@router.get("/match", response_model=list[DreamOut])
def match_dreams(
    participation_format: ParticipationFormat = Query(...),
    person_type:          PersonType           = Query(...),
    max_budget:           Decimal              = Query(...),
    db: Session = Depends(get_db),
):
    """Smart Match: up to 3 random incomplete dreams matching the criteria. Public."""
    matches = (
        db.query(Dream)
        .filter(
            Dream.is_completed         == False,
            Dream.participation_format == participation_format,
            Dream.person_type          == person_type,
            Dream.target_budget        <= max_budget,
        )
        .all()
    )
    if not matches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No dreams match your criteria")
    return random.sample(matches, min(3, len(matches)))


@router.get("/{dream_id}", response_model=DreamOutWithOwner)
def get_dream(dream_id: str, db: Session = Depends(get_db)):
    """Get full details of a single dream. Public."""
    return _get_dream_or_404(dream_id, db)


# ─── Authenticated writes ─────────────────────────────────────────────────────

@router.post("", response_model=DreamOut, status_code=status.HTTP_201_CREATED)
def create_dream(
    payload: DreamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a dream. Uses default image if none provided."""
    dream = Dream(
        owner_id=current_user.user_id,
        title=payload.title,
        description=payload.description,
        person_type=payload.person_type,
        participation_format=payload.participation_format,
        target_budget=payload.target_budget,
        city=payload.city,
        image_url=payload.image_url or DEFAULT_DREAM_IMAGE,
    )
    db.add(dream)
    db.commit()
    db.refresh(dream)
    return dream


@router.put("/{dream_id}", response_model=DreamOut)
def update_dream(
    dream_id: str,
    payload: DreamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a dream. Owner or admin only."""
    dream = _get_dream_or_404(dream_id, db)
    _require_ownership_or_admin(dream, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dream, field, value)

    db.commit()
    db.refresh(dream)
    return dream


@router.delete("/{dream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dream(
    dream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dream. Owner or admin only."""
    dream = _get_dream_or_404(dream_id, db)
    _require_ownership_or_admin(dream, current_user)
    db.delete(dream)
    db.commit()
