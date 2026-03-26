from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal

from app.database import get_db
from app.models.models import Dream, User

router = APIRouter(prefix="/statistics", tags=["Statistics"])


class StatisticsOut(BaseModel):
    total_users:             int
    completed_dreams_count:  int
    completed_dreams_budget: Decimal
    unique_cities_count:     int


@router.get("", response_model=StatisticsOut)
def get_statistics(db: Session = Depends(get_db)):
    """Public endpoint. Returns platform-wide stats."""

    total_users = db.query(func.count(User.user_id)).scalar()

    completed_dreams_count = (
        db.query(func.count(Dream.dream_id))
        .filter(Dream.is_completed == True)
        .scalar()
    )

    completed_dreams_budget = (
        db.query(func.coalesce(func.sum(Dream.target_budget), 0))
        .filter(Dream.is_completed == True)
        .scalar()
    )

    unique_cities_count = (
        db.query(func.count(func.distinct(Dream.city)))
        .filter(Dream.is_completed == True)
        .scalar()
    )

    return {
        "total_users":             total_users,
        "completed_dreams_count":  completed_dreams_count,
        "completed_dreams_budget": completed_dreams_budget,
        "unique_cities_count":     unique_cities_count,
    }
