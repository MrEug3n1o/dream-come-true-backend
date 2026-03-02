"""Tests for /users/me and /users/me/dreams"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.models import Dream, ParticipationFormat
from tests.conftest import auth_headers


class TestUserProfile:
    def test_get_my_profile(self, client: TestClient, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.get("/users/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == donor_user.email
        assert data["role"] == "donor"
        assert "password_hash" not in data

    def test_get_my_profile_dreamer(self, client: TestClient, dreamer_user):
        headers = auth_headers(client, dreamer_user.email, "dream123")
        resp = client.get("/users/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["person_type"] == "child"

    def test_get_profile_requires_auth(self, client: TestClient):
        resp = client.get("/users/me")
        assert resp.status_code == 401


class TestMyDreams:
    def test_get_my_dreams_empty(self, client: TestClient, dreamer_user):
        headers = auth_headers(client, dreamer_user.email, "dream123")
        resp = client.get("/users/me/dreams", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_my_dreams_with_data(self, client: TestClient, dreamer_user, db: Session):
        for i in range(3):
            db.add(Dream(
                dreamer_id=dreamer_user.user_id,
                title=f"My Dream {i}",
                description="desc",
                participation_format=ParticipationFormat.ONLINE,
                target_budget=50,
                is_completed=False,
            ))
        db.commit()

        headers = auth_headers(client, dreamer_user.email, "dream123")
        resp = client.get("/users/me/dreams", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3
        titles = [d["title"] for d in resp.json()]
        assert all(t.startswith("My Dream") for t in titles)

    def test_my_dreams_only_returns_own(self, client: TestClient, dreamer_user, sample_dream, db: Session):
        """A user should only see their own dreams, not others'."""
        from app.models.models import User, UserRole
        from app.auth import hash_password

        other_dreamer = User(
            full_name="Other", email="other@t.com",
            password_hash=hash_password("other123"), role=UserRole.DREAMER,
        )
        db.add(other_dreamer)
        db.commit()
        db.refresh(other_dreamer)

        db.add(Dream(
            dreamer_id=other_dreamer.user_id, title="Other's Dream",
            description="d", participation_format=ParticipationFormat.OFFLINE,
            target_budget=30, is_completed=False,
        ))
        db.commit()

        headers = auth_headers(client, dreamer_user.email, "dream123")
        resp = client.get("/users/me/dreams", headers=headers)
        assert resp.status_code == 200
        # sample_dream belongs to dreamer_user — should see only that
        dream_ids = [d["dreamer_id"] for d in resp.json()]
        assert all(did == dreamer_user.user_id for did in dream_ids)

    def test_my_dreams_requires_auth(self, client: TestClient):
        resp = client.get("/users/me/dreams")
        assert resp.status_code == 401
