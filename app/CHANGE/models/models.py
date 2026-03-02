import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Text, Numeric,
    DateTime, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    DREAMER = "dreamer"
    ADMIN = "admin"
    DONOR = "donor"


class PersonType(str, enum.Enum):
    VETERAN = "veteran"
    ELDERLY = "elderly"
    CHILD = "child"
    ANIMAL_SHELTER = "animal_shelter"
    OTHER = "other"


class ParticipationFormat(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"



class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.DONOR, nullable=False)
    person_type = Column(Enum(PersonType), nullable=True)  # relevant when role=DREAMER
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dreams = relationship("Dream", back_populates="dreamer", foreign_keys="Dream.dreamer_id")


class Dream(Base):
    __tablename__ = "dreams"

    dream_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    dreamer_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    participation_format = Column(Enum(ParticipationFormat), nullable=False)
    target_budget = Column(Numeric(10, 2), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    dreamer = relationship("User", back_populates="dreams", foreign_keys=[dreamer_id])
