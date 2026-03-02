from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.models import UserRole, PersonType, ParticipationFormat


# ─── Auth & User ─────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.DONOR
    person_type: Optional[PersonType] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: UserRole
    person_type: Optional[PersonType]
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ─── Dream ───────────────────────────────────────────────────────────────────

class DreamCreate(BaseModel):
    title: str
    description: str
    participation_format: ParticipationFormat
    target_budget: Decimal
    dreamer_id: Optional[str] = None  # Admin can override; otherwise defaults to current user


class DreamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    participation_format: Optional[ParticipationFormat] = None
    target_budget: Optional[Decimal] = None


class DreamOut(BaseModel):
    dream_id: str
    dreamer_id: str
    title: str
    description: str
    participation_format: ParticipationFormat
    target_budget: Decimal
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DreamOutWithDreamer(DreamOut):
    dreamer: Optional[UserOut] = None
