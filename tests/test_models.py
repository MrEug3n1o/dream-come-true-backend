from app.models.models import User, Dream, UserRole, PersonType, ParticipationFormat, DEFAULT_DREAM_IMAGE, generate_uuid


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
        assert not hasattr(User, "person_type")


class TestDreamModel:
    def _make_user(self, db, suffix=""):
        user = User(full_name="U", email=f"u{suffix}@t.com", password_hash="x", role=UserRole.USER)
        db.add(user); db.commit(); db.refresh(user)
        return user

    def _make_dream(self, db, user, **kwargs):
        defaults = dict(
            owner_id=user.user_id,
            title="T",
            description="D",
            person_type=PersonType.CHILD,
            participation_format=ParticipationFormat.ONLINE,
            target_budget=50,
            city="Kyiv",
        )
        defaults.update(kwargs)
        dream = Dream(**defaults)
        db.add(dream); db.commit(); db.refresh(dream)
        return dream

    def test_uuid_pk(self, db):
        user = self._make_user(db, "1")
        dream = self._make_dream(db, user)
        assert len(dream.dream_id) == 36

    def test_person_type_on_dream(self, db):
        user = self._make_user(db, "2")
        dream = self._make_dream(db, user, person_type=PersonType.VETERAN)
        assert dream.person_type == PersonType.VETERAN

    def test_city_stored(self, db):
        user = self._make_user(db, "3")
        dream = self._make_dream(db, user, city="Lviv")
        assert dream.city == "Lviv"

    def test_default_image_url(self, db):
        user = self._make_user(db, "4")
        dream = self._make_dream(db, user)
        assert dream.image_url == DEFAULT_DREAM_IMAGE

    def test_custom_image_url(self, db):
        user = self._make_user(db, "5")
        dream = self._make_dream(db, user, image_url="https://example.com/img.jpg")
        assert dream.image_url == "https://example.com/img.jpg"

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
        user = self._make_user(db, "6")
        dream = self._make_dream(db, user)
        assert dream.is_completed is False

    def test_owner_relationship(self, db):
        user = self._make_user(db, "7")
        dream = self._make_dream(db, user)
        assert dream.owner.user_id == user.user_id
