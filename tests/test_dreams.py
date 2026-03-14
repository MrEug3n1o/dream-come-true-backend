import pytest
from tests.conftest import login
from app.models.models import DEFAULT_DREAM_IMAGE

DREAM_PAYLOAD = {
    "title": "Learn Guitar",
    "description": "An elderly person dreams of learning guitar.",
    "person_type": "elderly",
    "participation_format": "online",
    "target_budget": 80.0,
    "city": "Kyiv",
}


class TestListDreams:
    def test_list_dreams_guest_accessible(self, client):
        assert client.get("/dreams").status_code == 200

    def test_list_dreams_empty(self, client):
        assert client.get("/dreams").json() == []

    def test_filter_by_participation_format(self, client, sample_dream):
        assert len(client.get("/dreams?participation_format=online").json()) == 1
        assert len(client.get("/dreams?participation_format=offline").json()) == 0

    def test_filter_by_person_type(self, client, sample_dream):
        assert len(client.get("/dreams?person_type=child").json()) == 1
        assert len(client.get("/dreams?person_type=elderly").json()) == 0

    def test_filter_by_max_budget(self, client, sample_dream):
        assert len(client.get("/dreams?max_budget=200").json()) == 1
        assert len(client.get("/dreams?max_budget=10").json()) == 0

    def test_filter_by_city(self, client, sample_dream):
        assert len(client.get("/dreams?city=Kyiv").json()) == 1
        assert len(client.get("/dreams?city=London").json()) == 0

    def test_filter_city_case_insensitive(self, client, sample_dream):
        assert len(client.get("/dreams?city=kyiv").json()) == 1

    def test_filter_by_is_completed(self, client, sample_dream, completed_dream):
        assert len(client.get("/dreams?is_completed=false").json()) == 1
        assert len(client.get("/dreams?is_completed=true").json()) == 1

    def test_sort_by_budget(self, client, sample_dream, completed_dream):
        data = client.get("/dreams?sort_by=budget").json()
        budgets = [float(d["target_budget"]) for d in data]
        assert budgets == sorted(budgets)


class TestGetDream:
    def test_get_by_id(self, client, sample_dream):
        resp = client.get(f"/dreams/{sample_dream.dream_id}")
        assert resp.status_code == 200

    def test_get_includes_city_and_image(self, client, sample_dream):
        data = client.get(f"/dreams/{sample_dream.dream_id}").json()
        assert data["city"] == "Kyiv"
        assert "image_url" in data

    def test_get_not_found(self, client):
        assert client.get("/dreams/nonexistent-id").status_code == 404


class TestCreateDream:
    def test_create_success(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.post("/dreams", json=DREAM_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Learn Guitar"
        assert data["city"] == "Kyiv"
        assert data["owner_id"] == regular_user.user_id

    def test_create_uses_default_image(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.post("/dreams", json=DREAM_PAYLOAD)
        assert resp.json()["image_url"] == DEFAULT_DREAM_IMAGE

    def test_create_uses_provided_image(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        payload = {**DREAM_PAYLOAD, "image_url": "https://example.com/img.jpg"}
        assert client.post("/dreams", json=payload).json()["image_url"] == "https://example.com/img.jpg"

    def test_create_requires_auth(self, client):
        assert client.post("/dreams", json=DREAM_PAYLOAD).status_code == 401

    def test_create_requires_city(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        payload = {k: v for k, v in DREAM_PAYLOAD.items() if k != "city"}
        assert client.post("/dreams", json=payload).status_code == 422

    def test_budget_over_limit_rejected(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        payload = {**DREAM_PAYLOAD, "target_budget": 20000}
        assert client.post("/dreams", json=payload).status_code == 422

    def test_budget_at_limit_accepted(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        payload = {**DREAM_PAYLOAD, "target_budget": 15000}
        assert client.post("/dreams", json=payload).status_code == 201

    def test_budget_zero_rejected(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        payload = {**DREAM_PAYLOAD, "target_budget": 0}
        assert client.post("/dreams", json=payload).status_code == 422


class TestUpdateDream:
    def test_owner_can_update(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_owner_can_update_city(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"city": "Lviv"}).json()["city"] == "Lviv"

    def test_update_budget_over_limit_rejected(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"target_budget": 20000}).status_code == 422

    def test_admin_can_update_any(self, client, sample_dream, admin_user):
        login(client, "admin@test.com", "admin123")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "Admin"}).status_code == 200

    def test_other_user_cannot_update(self, client, sample_dream, another_user):
        login(client, "another@test.com", "another123")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "x"}).status_code == 403

    def test_update_requires_auth(self, client, sample_dream):
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "x"}).status_code == 401


class TestDeleteDream:
    def test_owner_can_delete(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.delete(f"/dreams/{sample_dream.dream_id}").status_code == 204

    def test_admin_can_delete_any(self, client, sample_dream, admin_user):
        login(client, "admin@test.com", "admin123")
        assert client.delete(f"/dreams/{sample_dream.dream_id}").status_code == 204

    def test_other_user_cannot_delete(self, client, sample_dream, another_user):
        login(client, "another@test.com", "another123")
        assert client.delete(f"/dreams/{sample_dream.dream_id}").status_code == 403

    def test_delete_requires_auth(self, client, sample_dream):
        assert client.delete(f"/dreams/{sample_dream.dream_id}").status_code == 401


class TestMatchDreams:
    def test_match_returns_results(self, client, sample_dream):
        resp = client.get("/dreams/match?participation_format=online&person_type=child&max_budget=200")
        assert resp.status_code == 200

    def test_match_excludes_completed(self, client, completed_dream):
        assert client.get("/dreams/match?participation_format=offline&person_type=elderly&max_budget=200").status_code == 404

    def test_match_respects_budget(self, client, sample_dream):
        assert client.get("/dreams/match?participation_format=online&person_type=child&max_budget=10").status_code == 404

    def test_match_missing_params(self, client):
        assert client.get("/dreams/match").status_code == 422
