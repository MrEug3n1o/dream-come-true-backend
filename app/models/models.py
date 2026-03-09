import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Numeric, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def enum_values(e):
    """Always store the .value (lowercase string) not the enum name."""
    return [m.value for m in e]


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    USER  = "user"
    ADMIN = "admin"


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


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, values_callable=enum_values), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dreams = relationship("Dream", back_populates="owner", foreign_keys="Dream.owner_id")


class Dream(Base):
    __tablename__ = "dreams"

    dream_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    person_type = Column(Enum(PersonType, values_callable=enum_values), nullable=False)
    participation_format = Column(Enum(ParticipationFormat, values_callable=enum_values), nullable=False)
    target_budget = Column(Numeric(10, 2), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="dreams", foreign_keys=[owner_id])


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    token = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
