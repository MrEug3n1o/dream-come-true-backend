import pytest
from tests.conftest import auth_headers

DREAM_PAYLOAD = {
    "title": "Learn Guitar",
    "description": "An elderly person dreams of learning guitar.",
    "person_type": "elderly",
    "participation_format": "online",
    "target_budget": 80.0,
}


class TestListDreams:
    def test_list_dreams_guest_accessible(self, client):
        assert client.get("/dreams").status_code == 200

    def test_list_dreams_empty(self, client):
        assert client.get("/dreams").json() == []

    def test_list_returns_created_dream(self, client, sample_dream):
        data = client.get("/dreams").json()
        assert len(data) == 1
        assert data[0]["title"] == "Learn Piano Online"

    def test_filter_by_participation_format(self, client, sample_dream):
        assert len(client.get("/dreams?participation_format=online").json()) == 1
        assert len(client.get("/dreams?participation_format=offline").json()) == 0

    def test_filter_by_person_type(self, client, sample_dream):
        assert len(client.get("/dreams?person_type=child").json()) == 1
        assert len(client.get("/dreams?person_type=elderly").json()) == 0

    def test_filter_by_max_budget(self, client, sample_dream):
        assert len(client.get("/dreams?max_budget=200").json()) == 1
        assert len(client.get("/dreams?max_budget=10").json()) == 0

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
        assert resp.json()["dream_id"] == sample_dream.dream_id

    def test_get_includes_owner(self, client, sample_dream):
        data = client.get(f"/dreams/{sample_dream.dream_id}").json()
        assert "owner" in data
        assert data["owner"]["email"] == "user@test.com"

    def test_get_not_found(self, client):
        assert client.get("/dreams/nonexistent-id").status_code == 404


class TestCreateDream:
    def test_create_success(self, client, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        resp = client.post("/dreams", json=DREAM_PAYLOAD, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Learn Guitar"
        assert data["owner_id"] == regular_user.user_id
        assert data["person_type"] == "elderly"

    def test_create_requires_auth(self, client):
        assert client.post("/dreams", json=DREAM_PAYLOAD).status_code == 401

    def test_create_missing_person_type(self, client, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        payload = {**DREAM_PAYLOAD}
        del payload["person_type"]
        assert client.post("/dreams", json=payload, headers=headers).status_code == 422


class TestUpdateDream:
    def test_owner_can_update(self, client, sample_dream, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        resp = client.put(f"/dreams/{sample_dream.dream_id}",
                          json={"title": "Updated Title"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_admin_can_update_any(self, client, sample_dream, admin_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        resp = client.put(f"/dreams/{sample_dream.dream_id}",
                          json={"title": "Admin Updated"}, headers=headers)
        assert resp.status_code == 200

    def test_other_user_cannot_update(self, client, sample_dream, another_user):
        headers = auth_headers(client, "another@test.com", "another123")
        resp = client.put(f"/dreams/{sample_dream.dream_id}",
                          json={"title": "Stolen"}, headers=headers)
        assert resp.status_code == 403

    def test_update_requires_auth(self, client, sample_dream):
        resp = client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "x"})
        assert resp.status_code == 401

    def test_update_not_found(self, client, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        assert client.put("/dreams/bad-id", json={"title": "x"}, headers=headers).status_code == 404


class TestDeleteDream:
    def test_owner_can_delete(self, client, sample_dream, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        assert client.delete(f"/dreams/{sample_dream.dream_id}", headers=headers).status_code == 204

    def test_admin_can_delete_any(self, client, sample_dream, admin_user):
        headers = auth_headers(client, "admin@test.com", "admin123")
        assert client.delete(f"/dreams/{sample_dream.dream_id}", headers=headers).status_code == 204

    def test_other_user_cannot_delete(self, client, sample_dream, another_user):
        headers = auth_headers(client, "another@test.com", "another123")
        assert client.delete(f"/dreams/{sample_dream.dream_id}", headers=headers).status_code == 403

    def test_delete_requires_auth(self, client, sample_dream):
        assert client.delete(f"/dreams/{sample_dream.dream_id}").status_code == 401

    def test_delete_not_found(self, client, regular_user):
        headers = auth_headers(client, "user@test.com", "user1234")
        assert client.delete("/dreams/bad-id", headers=headers).status_code == 404


class TestMatchDreams:
    def test_match_returns_results(self, client, sample_dream):
        resp = client.get("/dreams/match?participation_format=online&person_type=child&max_budget=200")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_match_excludes_completed(self, client, completed_dream):
        resp = client.get("/dreams/match?participation_format=offline&person_type=elderly&max_budget=200")
        assert resp.status_code == 404  # completed dreams excluded

    def test_match_respects_budget(self, client, sample_dream):
        resp = client.get("/dreams/match?participation_format=online&person_type=child&max_budget=10")
        assert resp.status_code == 404  # budget too low

    def test_match_missing_params(self, client):
        assert client.get("/dreams/match").status_code == 422
