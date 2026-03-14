from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.models.models import UserRole, PersonType, ParticipationFormat

MAX_BUDGET = Decimal("15000")

# ─── Auth & User ─────────────────────────────────────────────────────────────

class UserLogin(BaseModel):
    email: EmailStr
    password: str


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


class UserOut(BaseModel):
    user_id:    str
    full_name:  str
    email:      str
    role:       UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    token_type: str = "bearer"
    user_role:  UserRole


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ─── Dream ───────────────────────────────────────────────────────────────────

class DreamCreate(BaseModel):
    title:                str
    description:          str
    person_type:          PersonType
    participation_format: ParticipationFormat
    target_budget:        Decimal
    city:                 str
    image_url:            Optional[str] = None

    @field_validator("target_budget")
    @classmethod
    def budget_limit(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Budget must be greater than 0")
        if v > MAX_BUDGET:
            raise ValueError(f"Budget cannot exceed {MAX_BUDGET}")
        return v


class DreamUpdate(BaseModel):
    title:                Optional[str]                  = None
    description:          Optional[str]                  = None
    person_type:          Optional[PersonType]           = None
    participation_format: Optional[ParticipationFormat] = None
    target_budget:        Optional[Decimal]              = None
    city:                 Optional[str]                  = None
    image_url:            Optional[str]                  = None
    is_completed:         Optional[bool]                 = None

    @field_validator("target_budget")
    @classmethod
    def budget_limit(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= 0:
                raise ValueError("Budget must be greater than 0")
            if v > MAX_BUDGET:
                raise ValueError(f"Budget cannot exceed {MAX_BUDGET}")
        return v


class DreamOut(BaseModel):
    dream_id:             str
    owner_id:             str
    title:                str
    description:          str
    person_type:          PersonType
    participation_format: ParticipationFormat
    target_budget:        Decimal
    city:                 str
    image_url:            str
    is_completed:         bool
    created_at:           datetime
    updated_at:           datetime

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
