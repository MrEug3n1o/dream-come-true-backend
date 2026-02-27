from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.models import DreamFormat, PersonType, DreamStatus


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
    id: int
    full_name: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class DreamCreate(BaseModel):
    title: str
    description: str
    format: DreamFormat
    person_type: PersonType
    budget: Decimal
    image_url: Optional[str] = None


class DreamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    format: Optional[DreamFormat] = None
    person_type: Optional[PersonType] = None
    budget: Optional[Decimal] = None
    image_url: Optional[str] = None


class DreamStatusUpdate(BaseModel):
    status: DreamStatus


class DreamOut(BaseModel):
    id: int
    title: str
    description: str
    format: DreamFormat
    person_type: PersonType
    budget: Decimal
    status: DreamStatus
    image_url: Optional[str]
    fulfilled_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DreamOutWithFulfiller(DreamOut):
    fulfilled_by: Optional[UserOut] = None
