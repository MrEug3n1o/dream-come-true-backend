"""Tests for /dreams endpoints — list, filter, match, detail, fulfill"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.models import Dream, User, ParticipationFormat, PersonType, UserRole
from app.auth import hash_password
from tests.conftest import auth_headers


class TestListDreams:
    def test_list_dreams_guest_accessible(self, client: TestClient, sample_dream):
        resp = client.get("/dreams")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_dreams_empty(self, client: TestClient):
        resp = client.get("/dreams")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_participation_format(self, client: TestClient, db: Session, dreamer_user):
        db.add(Dream(
            dreamer_id=dreamer_user.user_id, title="Online Dream",
            description="desc", participation_format=ParticipationFormat.ONLINE,
            target_budget=50, is_completed=False,
        ))
        db.add(Dream(
            dreamer_id=dreamer_user.user_id, title="Offline Dream",
            description="desc", participation_format=ParticipationFormat.OFFLINE,
            target_budget=50, is_completed=False,
        ))
        db.add(Dream(
            dreamer_id=dreamer_user.user_id, title="Hybrid Dream",
            description="desc", participation_format=ParticipationFormat.HYBRID,
            target_budget=50, is_completed=False,
        ))
        db.commit()

        resp = client.get("/dreams?participation_format=online")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["title"] == "Online Dream"

    def test_filter_by_max_budget(self, client: TestClient, db: Session, dreamer_user):
        for budget in [30, 60, 100]:
            db.add(Dream(
                dreamer_id=dreamer_user.user_id, title=f"Dream {budget}",
                description="desc", participation_format=ParticipationFormat.ONLINE,
                target_budget=budget, is_completed=False,
            ))
        db.commit()

        resp = client.get("/dreams?max_budget=60")
        assert resp.status_code == 200
        budgets = [d["target_budget"] for d in resp.json()]
        assert all(float(b) <= 60 for b in budgets)
        assert len(budgets) == 2

    def test_filter_by_is_completed(self, client: TestClient, sample_dream, completed_dream):
        resp = client.get("/dreams?is_completed=false")
        assert resp.status_code == 200
        assert all(not d["is_completed"] for d in resp.json())

        resp = client.get("/dreams?is_completed=true")
        assert resp.status_code == 200
        assert all(d["is_completed"] for d in resp.json())

    def test_filter_by_person_type(self, client: TestClient, db: Session):
        child_user = User(
            full_name="Child", email="child@t.com",
            password_hash=hash_password("x"), role=UserRole.DREAMER,
            person_type=PersonType.CHILD,
        )
        elderly_user = User(
            full_name="Elder", email="elder@t.com",
            password_hash=hash_password("x"), role=UserRole.DREAMER,
            person_type=PersonType.ELDERLY,
        )
        db.add_all([child_user, elderly_user])
        db.commit()
        db.refresh(child_user)
        db.refresh(elderly_user)

        db.add(Dream(
            dreamer_id=child_user.user_id, title="Child Dream",
            description="d", participation_format=ParticipationFormat.ONLINE,
            target_budget=50, is_completed=False,
        ))
        db.add(Dream(
            dreamer_id=elderly_user.user_id, title="Elderly Dream",
            description="d", participation_format=ParticipationFormat.OFFLINE,
            target_budget=80, is_completed=False,
        ))
        db.commit()

        resp = client.get("/dreams?person_type=child")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Child Dream"

    def test_sort_by_budget(self, client: TestClient, db: Session, dreamer_user):
        for b in [80, 20, 50]:
            db.add(Dream(
                dreamer_id=dreamer_user.user_id, title=f"Dream {b}",
                description="d", participation_format=ParticipationFormat.ONLINE,
                target_budget=b, is_completed=False,
            ))
        db.commit()

        resp = client.get("/dreams?sort_by=budget")
        budgets = [float(d["target_budget"]) for d in resp.json()]
        assert budgets == sorted(budgets)


class TestGetDream:
    def test_get_dream_by_id(self, client: TestClient, sample_dream):
        resp = client.get(f"/dreams/{sample_dream.dream_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dream_id"] == sample_dream.dream_id
        assert data["title"] == sample_dream.title
        assert "dreamer" in data  # includes nested dreamer info

    def test_get_dream_not_found(self, client: TestClient):
        resp = client.get("/dreams/nonexistent-uuid")
        assert resp.status_code == 404

    def test_get_dream_includes_dreamer_info(self, client: TestClient, sample_dream, dreamer_user):
        resp = client.get(f"/dreams/{sample_dream.dream_id}")
        assert resp.status_code == 200
        dreamer = resp.json()["dreamer"]
        assert dreamer["user_id"] == dreamer_user.user_id
        assert dreamer["person_type"] == "child"


class TestFulfillDream:
    def test_fulfill_dream_as_donor(self, client: TestClient, sample_dream, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.post(f"/dreams/{sample_dream.dream_id}/fulfill", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_fulfill_already_completed_dream(self, client: TestClient, completed_dream, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.post(f"/dreams/{completed_dream.dream_id}/fulfill", headers=headers)
        assert resp.status_code == 409
        assert "already been completed" in resp.json()["detail"]

    def test_fulfill_requires_auth(self, client: TestClient, sample_dream):
        resp = client.post(f"/dreams/{sample_dream.dream_id}/fulfill")
        assert resp.status_code == 401

    def test_fulfill_nonexistent_dream(self, client: TestClient, donor_user):
        headers = auth_headers(client, donor_user.email, "donor123")
        resp = client.post("/dreams/does-not-exist/fulfill", headers=headers)
        assert resp.status_code == 404


class TestMatchDreams:
    def test_match_returns_up_to_3(self, client: TestClient, db: Session):
        dreamer = User(
            full_name="Child D", email="cd@t.com",
            password_hash=hash_password("x"), role=UserRole.DREAMER,
            person_type=PersonType.CHILD,
        )
        db.add(dreamer)
        db.commit()
        db.refresh(dreamer)

        for i in range(5):
            db.add(Dream(
                dreamer_id=dreamer.user_id, title=f"Dream {i}",
                description="d", participation_format=ParticipationFormat.ONLINE,
                target_budget=50, is_completed=False,
            ))
        db.commit()

        resp = client.get("/dreams/match?participation_format=online&person_type=child&max_budget=100")
        assert resp.status_code == 200
        assert len(resp.json()) <= 3

    def test_match_excludes_completed(self, client: TestClient, db: Session):
        dreamer = User(
            full_name="Elder D", email="ed@t.com",
            password_hash=hash_password("x"), role=UserRole.DREAMER,
            person_type=PersonType.ELDERLY,
        )
        db.add(dreamer)
        db.commit()
        db.refresh(dreamer)

        db.add(Dream(
            dreamer_id=dreamer.user_id, title="Completed",
            description="d", participation_format=ParticipationFormat.OFFLINE,
            target_budget=50, is_completed=True,
        ))
        db.commit()

        resp = client.get("/dreams/match?participation_format=offline&person_type=elderly&max_budget=100")
        assert resp.status_code == 404

    def test_match_respects_budget(self, client: TestClient, db: Session):
        dreamer = User(
            full_name="V", email="v@t.com",
            password_hash=hash_password("x"), role=UserRole.DREAMER,
            person_type=PersonType.VETERAN,
        )
        db.add(dreamer)
        db.commit()
        db.refresh(dreamer)

        db.add(Dream(
            dreamer_id=dreamer.user_id, title="Cheap",
            description="d", participation_format=ParticipationFormat.HYBRID,
            target_budget=40, is_completed=False,
        ))
        db.add(Dream(
            dreamer_id=dreamer.user_id, title="Expensive",
            description="d", participation_format=ParticipationFormat.HYBRID,
            target_budget=500, is_completed=False,
        ))
        db.commit()

        resp = client.get("/dreams/match?participation_format=hybrid&person_type=veteran&max_budget=100")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Cheap"

    def test_match_missing_params(self, client: TestClient):
        resp = client.get("/dreams/match?participation_format=online")
        assert resp.status_code == 422

    def test_match_no_results(self, client: TestClient):
        resp = client.get("/dreams/match?participation_format=online&person_type=child&max_budget=1")
        assert resp.status_code == 404
