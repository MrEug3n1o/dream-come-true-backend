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
    person_type: PersonType
    participation_format: ParticipationFormat
    target_budget: Decimal


class DreamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    person_type: Optional[PersonType] = None
    participation_format: Optional[ParticipationFormat] = None
    target_budget: Optional[Decimal] = None
    is_completed: Optional[bool] = None


class DreamOut(BaseModel):
    dream_id: str
    owner_id: str
    title: str
    description: str
    person_type: PersonType
    participation_format: ParticipationFormat
    target_budget: Decimal
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DreamOutWithOwner(DreamOut):
    owner: Optional[UserOut] = None

# ─── Password Reset ───────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class MessageResponse(BaseModel):
    message: str
