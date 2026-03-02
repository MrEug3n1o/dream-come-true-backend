import random
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dream, ParticipationFormat, PersonType, User
from app.models.schemas import DreamOut, DreamOutWithDreamer
from app.auth import get_current_user

router = APIRouter(prefix="/dreams", tags=["Dreams"])


@router.get("", response_model=list[DreamOut])
def list_dreams(
    participation_format: Optional[ParticipationFormat] = Query(None),
    person_type: Optional[PersonType] = Query(None, description="Filter by dreamer's person type"),
    max_budget: Optional[Decimal] = Query(None),
    is_completed: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None, description="'date' or 'budget'"),
    db: Session = Depends(get_db),
):
    """List all dreams with optional filtering. Accessible by guests."""
    query = db.query(Dream)

    if participation_format:
        query = query.filter(Dream.participation_format == participation_format)
    if person_type:
        query = query.join(User, Dream.dreamer_id == User.user_id)\
                     .filter(User.person_type == person_type)
    if max_budget is not None:
        query = query.filter(Dream.target_budget <= max_budget)
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
    person_type: PersonType = Query(...),
    max_budget: Decimal = Query(...),
    db: Session = Depends(get_db),
):
    """
    Smart Match: returns up to 3 randomised incomplete dreams
    matching format, dreamer person_type, and budget.
    """
    matches = (
        db.query(Dream)
        .join(User, Dream.dreamer_id == User.user_id)
        .filter(
            Dream.is_completed == False,
            Dream.participation_format == participation_format,
            User.person_type == person_type,
            Dream.target_budget <= max_budget,
        )
        .all()
    )

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No available dreams match your criteria."
        )

    return random.sample(matches, min(3, len(matches)))


@router.get("/{dream_id}", response_model=DreamOutWithDreamer)
def get_dream(dream_id: str, db: Session = Depends(get_db)):
    """Get full details of a specific dream."""
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")
    return dream


@router.post("/{dream_id}/fulfill", response_model=DreamOut)
def fulfill_dream(
    dream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a dream as completed. Authenticated donors only."""
    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")
    if dream.is_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dream has already been completed"
        )
    dream.is_completed = True
    db.commit()
    db.refresh(dream)
    return dream
