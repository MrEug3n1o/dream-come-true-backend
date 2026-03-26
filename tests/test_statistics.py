from app.models.models import Dream, PersonType, ParticipationFormat, DEFAULT_DREAM_IMAGE


def make_dream(db, owner_id, city, budget, is_completed):
    dream = Dream(
        owner_id=owner_id,
        title="Test Dream",
        description="Test",
        person_type=PersonType.CHILD,
        participation_format=ParticipationFormat.ONLINE,
        target_budget=budget,
        city=city,
        image_url=DEFAULT_DREAM_IMAGE,
        is_completed=is_completed,
    )
    db.add(dream)
    db.commit()
    return dream


class TestStatistics:
    def test_empty_db(self, client):
        resp = client.get("/statistics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] == 0
        assert data["completed_dreams_count"] == 0
        assert float(data["completed_dreams_budget"]) == 0
        assert data["unique_cities_count"] == 0

    def test_counts_users(self, client, regular_user, another_user):
        assert client.get("/statistics").json()["total_users"] == 2

    def test_counts_only_completed_dreams(self, client, regular_user, db):
        make_dream(db, regular_user.user_id, "Kyiv", 100, is_completed=True)
        make_dream(db, regular_user.user_id, "Lviv", 200, is_completed=False)
        data = client.get("/statistics").json()
        assert data["completed_dreams_count"] == 1

    def test_sums_completed_budget(self, client, regular_user, db):
        make_dream(db, regular_user.user_id, "Kyiv",  500, is_completed=True)
        make_dream(db, regular_user.user_id, "Lviv",  300, is_completed=True)
        make_dream(db, regular_user.user_id, "Odesa", 999, is_completed=False)
        data = client.get("/statistics").json()
        assert float(data["completed_dreams_budget"]) == 800.0

    def test_counts_unique_cities_of_completed(self, client, regular_user, db):
        make_dream(db, regular_user.user_id, "Kyiv",  100, is_completed=True)
        make_dream(db, regular_user.user_id, "Kyiv",  200, is_completed=True)   # duplicate
        make_dream(db, regular_user.user_id, "Lviv",  300, is_completed=True)
        make_dream(db, regular_user.user_id, "Odesa", 400, is_completed=False)  # not completed
        data = client.get("/statistics").json()
        assert data["unique_cities_count"] == 2   # Kyiv + Lviv only

    def test_is_public(self, client):
        """No auth required."""
        assert client.get("/statistics").status_code == 200

    def test_all_fields_present(self, client):
        data = client.get("/statistics").json()
        assert "total_users" in data
        assert "completed_dreams_count" in data
        assert "completed_dreams_budget" in data
        assert "unique_cities_count" in data
