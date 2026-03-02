"""Unit tests for ORM models — field defaults, enums, relationships."""
import pytest
from sqlalchemy.orm import Session
from app.models.models import (
    User, Dream, UserRole, PersonType, ParticipationFormat
)
from app.auth import hash_password


class TestUserModel:
    def test_user_gets_uuid_pk(self, db: Session):
        user = User(
            full_name="Test", email="t@t.com",
            password_hash=hash_password("pass"), role=UserRole.DONOR,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.user_id is not None
        assert len(user.user_id) == 36  # UUID format
        assert "-" in user.user_id

    def test_user_default_role_is_donor(self, db: Session):
        user = User(
            full_name="Test", email="t2@t.com",
            password_hash="hashed",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.role == UserRole.DONOR

    def test_user_all_roles(self, db: Session):
        for i, role in enumerate(UserRole):
            user = User(
                full_name=f"User {i}", email=f"r{i}@t.com",
                password_hash="hashed", role=role,
            )
            db.add(user)
        db.commit()

        users = db.query(User).all()
        roles = {u.role for u in users}
        assert roles == set(UserRole)

    def test_user_all_person_types(self, db: Session):
        for i, ptype in enumerate(PersonType):
            user = User(
                full_name=f"PT {i}", email=f"pt{i}@t.com",
                password_hash="h", role=UserRole.DREAMER,
                person_type=ptype,
            )
            db.add(user)
        db.commit()

        users = db.query(User).filter(User.role == UserRole.DREAMER).all()
        ptypes = {u.person_type for u in users}
        assert ptypes == set(PersonType)

    def test_user_person_type_nullable(self, db: Session):
        user = User(
            full_name="Donor", email="d@t.com",
            password_hash="h", role=UserRole.DONOR,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.person_type is None

    def test_user_created_at_auto(self, db: Session):
        user = User(
            full_name="T", email="ts@t.com", password_hash="h",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.created_at is not None

    def test_user_email_unique_constraint(self, db: Session):
        from sqlalchemy.exc import IntegrityError
        db.add(User(full_name="A", email="dup@t.com", password_hash="h"))
        db.commit()
        db.add(User(full_name="B", email="dup@t.com", password_hash="h"))
        with pytest.raises(IntegrityError):
            db.commit()


class TestDreamModel:
    def test_dream_gets_uuid_pk(self, db: Session, dreamer_user):
        dream = Dream(
            dreamer_id=dreamer_user.user_id, title="T",
            description="d", participation_format=ParticipationFormat.ONLINE,
            target_budget=50,
        )
        db.add(dream)
        db.commit()
        db.refresh(dream)
        assert dream.dream_id is not None
        assert len(dream.dream_id) == 36

    def test_dream_default_is_completed_false(self, db: Session, dreamer_user):
        dream = Dream(
            dreamer_id=dreamer_user.user_id, title="T",
            description="d", participation_format=ParticipationFormat.ONLINE,
            target_budget=50,
        )
        db.add(dream)
        db.commit()
        db.refresh(dream)
        assert dream.is_completed is False

    def test_dream_all_participation_formats(self, db: Session, dreamer_user):
        for fmt in ParticipationFormat:
            db.add(Dream(
                dreamer_id=dreamer_user.user_id, title=f"Dream {fmt}",
                description="d", participation_format=fmt, target_budget=10,
            ))
        db.commit()

        dreams = db.query(Dream).all()
        formats = {d.participation_format for d in dreams}
        assert formats == set(ParticipationFormat)

    def test_dream_dreamer_relationship(self, db: Session, dreamer_user):
        dream = Dream(
            dreamer_id=dreamer_user.user_id, title="T",
            description="d", participation_format=ParticipationFormat.HYBRID,
            target_budget=75,
        )
        db.add(dream)
        db.commit()
        db.refresh(dream)

        assert dream.dreamer is not None
        assert dream.dreamer.user_id == dreamer_user.user_id
        assert dream.dreamer.full_name == dreamer_user.full_name

    def test_user_dreams_backref(self, db: Session, dreamer_user):
        for i in range(3):
            db.add(Dream(
                dreamer_id=dreamer_user.user_id, title=f"D{i}",
                description="d", participation_format=ParticipationFormat.ONLINE,
                target_budget=10,
            ))
        db.commit()
        db.refresh(dreamer_user)
        assert len(dreamer_user.dreams) == 3

    def test_dream_timestamps(self, db: Session, dreamer_user):
        dream = Dream(
            dreamer_id=dreamer_user.user_id, title="T",
            description="d", participation_format=ParticipationFormat.ONLINE,
            target_budget=10,
        )
        db.add(dream)
        db.commit()
        db.refresh(dream)
        assert dream.created_at is not None
        assert dream.updated_at is not None
