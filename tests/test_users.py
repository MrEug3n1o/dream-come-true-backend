from tests.conftest import login


class TestUserProfile:
    def test_get_my_profile(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.get("/users/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"
        assert resp.json()["role"] == "user"

    def test_get_profile_requires_auth(self, client):
        assert client.get("/users/me").status_code == 401


class TestMyDreams:
    def test_my_dreams_empty(self, client, regular_user):
        login(client, "user@test.com", "user1234")
        assert client.get("/users/me/dreams").json() == []

    def test_my_dreams_with_data(self, client, regular_user, sample_dream):
        login(client, "user@test.com", "user1234")
        resp = client.get("/users/me/dreams")
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Learn Piano Online"

    def test_my_dreams_only_own(self, client, regular_user, another_user, sample_dream, db):
        from app.models.models import Dream, PersonType, ParticipationFormat, DEFAULT_DREAM_IMAGE
        other = Dream(
            owner_id=another_user.user_id,
            title="Another's Dream",
            description="Not yours",
            person_type=PersonType.VETERAN,
            participation_format=ParticipationFormat.HYBRID,
            target_budget=200,
            city="Odesa",
            image_url=DEFAULT_DREAM_IMAGE,
        )
        db.add(other); db.commit()

        login(client, "user@test.com", "user1234")
        resp = client.get("/users/me/dreams")
        assert len(resp.json()) == 1
        assert resp.json()[0]["owner_id"] == regular_user.user_id

    def test_my_dreams_requires_auth(self, client):
        assert client.get("/users/me/dreams").status_code == 401
