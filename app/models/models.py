import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Numeric,
    DateTime, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class DreamFormat(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class PersonType(str, enum.Enum):
    CHILD = "CHILD"
    ELDERLY = "ELDERLY"
    ANIMAL_SHELTER = "ANIMAL_SHELTER"
    OTHER = "OTHER"


class DreamStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    COMPLETED = "COMPLETED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fulfilled_dreams = relationship("Dream", back_populates="fulfilled_by")


class Dream(Base):
    __tablename__ = "dreams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    format = Column(Enum(DreamFormat), nullable=False)
    person_type = Column(Enum(PersonType), nullable=False)
    budget = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(DreamStatus), default=DreamStatus.AVAILABLE, nullable=False)
    image_url = Column(String(500), nullable=True)
    fulfilled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    fulfilled_by = relationship("User", back_populates="fulfilled_dreams")
