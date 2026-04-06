import io
from unittest.mock import patch
from tests.conftest import login
from app.models.models import DEFAULT_DREAM_IMAGE

FAKE_CLOUDINARY_URL = "https://res.cloudinary.com/demo/image/upload/dreams/test.jpg"

DREAM_FORM = {
    "title": "Learn Guitar",
    "description": "An elderly person dreams of learning guitar.",
    "person_type": "elderly",
    "participation_format": "online",
    "target_budget": "80.0",
    "city": "Kyiv",
}


def post_dream(client, data=None, image_file=None):
    form_data = data or DREAM_FORM
    if image_file:
        return client.post("/dreams", data=form_data, files={"image": image_file})
    return client.post("/dreams", data=form_data)


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
        assert client.get(f"/dreams/{sample_dream.dream_id}").status_code == 200

    def test_get_includes_city_and_image(self, client, sample_dream):
        data = client.get(f"/dreams/{sample_dream.dream_id}").json()
        assert data["city"] == "Kyiv"
        assert "image_url" in data

    def test_get_includes_owner(self, client, sample_dream):
        assert client.get(f"/dreams/{sample_dream.dream_id}").json()["owner"]["email"] == "user@test.com"

    def test_get_not_found(self, client):
        assert client.get("/dreams/nonexistent-id").status_code == 404


class TestCreateDream:
    def test_create_without_image_uses_default(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = post_dream(client)
        assert resp.status_code == 201
        assert resp.json()["image_url"] == DEFAULT_DREAM_IMAGE

    @patch("app.routers.dreams.cloudinary.uploader.upload")
    def test_create_with_image(self, mock_upload, client, regular_user):
        mock_upload.return_value = {"secure_url": FAKE_CLOUDINARY_URL}
        login(client, "user@test.com", "user1234")
        image = ("test.jpg", io.BytesIO(b"\xff\xd8\xff" + b"0" * 100), "image/jpeg")
        resp = post_dream(client, image_file=image)
        assert resp.status_code == 201
        assert resp.json()["image_url"] == FAKE_CLOUDINARY_URL

    def test_create_requires_auth(self, client):
        assert post_dream(client).status_code == 401

    def test_create_requires_city(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        data = {k: v for k, v in DREAM_FORM.items() if k != "city"}
        assert client.post("/dreams", data=data).status_code == 422

    def test_budget_over_limit_rejected(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert post_dream(client, data={**DREAM_FORM, "target_budget": "20000"}).status_code == 422

    def test_budget_at_limit_accepted(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert post_dream(client, data={**DREAM_FORM, "target_budget": "15000"}).status_code == 201

    def test_budget_zero_rejected(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert post_dream(client, data={**DREAM_FORM, "target_budget": "0"}).status_code == 422

    def test_rejects_non_image_file(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert post_dream(client, image_file=("doc.pdf", io.BytesIO(b"pdf"), "application/pdf")).status_code == 415

    def test_rejects_oversized_image(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        big = ("big.jpg", io.BytesIO(b"\xff\xd8\xff" + b"0" * 6 * 1024 * 1024), "image/jpeg")
        assert post_dream(client, image_file=big).status_code == 413


class TestCompleteDream:
    def test_any_auth_user_can_complete(self, client, sample_dream, another_user):
        login(client, "another@test.com", "another123")
        resp = client.patch(f"/dreams/{sample_dream.dream_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_owner_cannot_complete_own_dream(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.patch(f"/dreams/{sample_dream.dream_id}/complete")
        assert resp.status_code == 400
        assert "own dream" in resp.json()["detail"]

    def test_cannot_complete_already_completed(self, client, completed_dream, another_user):
        login(client, "another@test.com", "another123")
        resp = client.patch(f"/dreams/{completed_dream.dream_id}/complete")
        assert resp.status_code == 409

    def test_complete_requires_auth(self, client, sample_dream):
        assert client.patch(f"/dreams/{sample_dream.dream_id}/complete").status_code == 401

    def test_complete_not_found(self, client, another_user):
        login(client, "another@test.com", "another123")
        assert client.patch("/dreams/bad-id/complete").status_code == 404

    def test_admin_can_complete_any(self, client, sample_dream, admin_user):
        login(client, "admin@test.com", "admin123")
        resp = client.patch(f"/dreams/{sample_dream.dream_id}/complete")
        assert resp.status_code == 200


class TestUpdateDream:
    def test_owner_can_update(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_admin_can_update_any(self, client, sample_dream, admin_user):
        login(client, "admin@test.com", "admin123")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "Admin"}).status_code == 200

    def test_other_user_cannot_update(self, client, sample_dream, another_user):
        login(client, "another@test.com", "another123")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "x"}).status_code == 403

    def test_update_requires_auth(self, client, sample_dream):
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"title": "x"}).status_code == 401

    def test_update_budget_over_limit_rejected(self, client, sample_dream, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.put(f"/dreams/{sample_dream.dream_id}", json={"target_budget": 20000}).status_code == 422

    def test_update_not_found(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.put("/dreams/bad-id", json={"title": "x"}).status_code == 404


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

    def test_delete_not_found(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.delete("/dreams/bad-id").status_code == 404

class TestMatchDreams:
    def test_match_returns_results(self, client, sample_dream):
        assert client.get("/dreams/match?participation_format=online&person_type=child&max_budget=200").status_code == 200

    def test_match_excludes_completed(self, client, completed_dream):
        assert client.get("/dreams/match?participation_format=offline&person_type=elderly&max_budget=200").status_code == 404

    def test_match_respects_budget(self, client, sample_dream):
        assert client.get("/dreams/match?participation_format=online&person_type=child&max_budget=10").status_code == 404

    def test_match_missing_params(self, client):
        assert client.get("/dreams/match").status_code == 422
