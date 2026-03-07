from app.models.models import User, Dream, UserRole, PersonType, ParticipationFormat, generate_uuid


class TestUserModel:
    def test_uuid_pk(self, db):
        user = User(full_name="T", email="t@t.com", password_hash="x", role=UserRole.USER)
        db.add(user); db.commit(); db.refresh(user)
        assert len(user.user_id) == 36
        assert "-" in user.user_id

    def test_default_role_is_user(self, db):
        user = User(full_name="T", email="t2@t.com", password_hash="x")
        db.add(user); db.commit(); db.refresh(user)
        assert user.role == UserRole.USER

    def test_user_roles(self):
        assert set(UserRole) == {UserRole.USER, UserRole.ADMIN}

    def test_no_person_type_on_user(self):
        """person_type is now on Dream, not User."""
        assert not hasattr(User, "person_type")


class TestDreamModel:
    def _make_user(self, db, suffix=""):
        user = User(full_name="U", email=f"u{suffix}@t.com", password_hash="x", role=UserRole.USER)
        db.add(user); db.commit(); db.refresh(user)
        return user

    def test_uuid_pk(self, db):
        user = self._make_user(db, "1")
        dream = Dream(
            owner_id=user.user_id, title="T", description="D",
            person_type=PersonType.CHILD,
            participation_format=ParticipationFormat.ONLINE,
            target_budget=50,
        )
        db.add(dream); db.commit(); db.refresh(dream)
        assert len(dream.dream_id) == 36

    def test_person_type_on_dream(self, db):
        user = self._make_user(db, "2")
        dream = Dream(
            owner_id=user.user_id, title="T", description="D",
            person_type=PersonType.VETERAN,
            participation_format=ParticipationFormat.HYBRID,
            target_budget=100,
        )
        db.add(dream); db.commit(); db.refresh(dream)
        assert dream.person_type == PersonType.VETERAN

    def test_all_person_types(self):
        assert set(PersonType) == {
            PersonType.VETERAN, PersonType.ELDERLY, PersonType.CHILD,
            PersonType.ANIMAL_SHELTER, PersonType.OTHER
        }

    def test_all_formats(self):
        assert set(ParticipationFormat) == {
            ParticipationFormat.ONLINE, ParticipationFormat.OFFLINE, ParticipationFormat.HYBRID
        }

    def test_default_not_completed(self, db):
        user = self._make_user(db, "3")
        dream = Dream(
            owner_id=user.user_id, title="T", description="D",
            person_type=PersonType.OTHER,
            participation_format=ParticipationFormat.ONLINE,
            target_budget=10,
        )
        db.add(dream); db.commit(); db.refresh(dream)
        assert dream.is_completed is False

    def test_owner_relationship(self, db):
        user = self._make_user(db, "4")
        dream = Dream(
            owner_id=user.user_id, title="T", description="D",
            person_type=PersonType.CHILD,
            participation_format=ParticipationFormat.OFFLINE,
            target_budget=30,
        )
        db.add(dream); db.commit(); db.refresh(dream)
        assert dream.owner.user_id == user.user_id
