"""
Tests for Cloudinary image upload.
All Cloudinary calls are mocked — no real account needed.
"""
import io
from unittest.mock import patch, MagicMock
from tests.conftest import login

FAKE_URL = "https://res.cloudinary.com/demo/image/upload/dreams/user123/abc.jpg"


def make_upload_mock(secure_url: str = FAKE_URL):
    mock = MagicMock()
    mock.return_value = {"secure_url": secure_url}
    return mock


def jpeg_file(filename: str = "test.jpg", size_bytes: int = 1024):
    return (filename, io.BytesIO(b"\xff\xd8\xff" + b"0" * size_bytes), "image/jpeg")


class TestUploadImage:
    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_upload_success(self, mock_upload, client, regular_user):
        mock_upload.return_value = {"secure_url": FAKE_URL}
        login(client, "user@test.com", "user1234")
        resp = client.post("/images", files={"file": jpeg_file()})
        assert resp.status_code == 201
        assert resp.json()["image_url"] == FAKE_URL

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_upload_requires_auth(self, mock_upload, client):
        resp = client.post("/images", files={"file": jpeg_file()})
        assert resp.status_code == 401

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_rejects_non_image(self, mock_upload, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.post(
            "/images",
            files={"file": ("doc.pdf", io.BytesIO(b"pdf"), "application/pdf")},
        )
        assert resp.status_code == 415

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_rejects_oversized_file(self, mock_upload, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.post(
            "/images",
            files={"file": jpeg_file("big.jpg", size_bytes=6 * 1024 * 1024)},
        )
        assert resp.status_code == 413

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_accepts_png(self, mock_upload, client, regular_user):
        mock_upload.return_value = {"secure_url": FAKE_URL}
        login(client, "user@test.com", "user1234")
        resp = client.post(
            "/images",
            files={"file": ("photo.png", io.BytesIO(b"\x89PNG" + b"0" * 100), "image/png")},
        )
        assert resp.status_code == 201

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_cloudinary_failure_returns_503(self, mock_upload, client, regular_user):
        mock_upload.side_effect = Exception("Cloudinary unavailable")
        login(client, "user@test.com", "user1234")
        resp = client.post("/images", files={"file": jpeg_file()})
        assert resp.status_code == 503

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_public_id_contains_user_id(self, mock_upload, client, regular_user):
        mock_upload.return_value = {"secure_url": FAKE_URL}
        login(client, "user@test.com", "user1234")
        client.post("/images", files={"file": jpeg_file()})
        call_kwargs = mock_upload.call_args[1]
        assert regular_user.user_id in call_kwargs["public_id"]


class TestUploadDreamImage:
    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_upload_and_attach(self, mock_upload, client, regular_user, sample_dream):
        mock_upload.return_value = {"secure_url": FAKE_URL}
        login(client, "user@test.com", "user1234")
        resp = client.post(
            f"/images/dreams/{sample_dream.dream_id}",
            files={"file": jpeg_file()},
        )
        assert resp.status_code == 200
        assert resp.json()["image_url"] == FAKE_URL

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_dream_image_updated_in_db(self, mock_upload, client, regular_user, sample_dream, db):
        mock_upload.return_value = {"secure_url": FAKE_URL}
        login(client, "user@test.com", "user1234")
        client.post(
            f"/images/dreams/{sample_dream.dream_id}",
            files={"file": jpeg_file()},
        )
        db.expire_all()
        from app.models.models import Dream
        updated = db.query(Dream).filter(Dream.dream_id == sample_dream.dream_id).first()
        assert updated.image_url == FAKE_URL

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_other_user_cannot_upload(self, mock_upload, client, another_user, sample_dream):
        login(client, "another@test.com", "another123")
        resp = client.post(
            f"/images/dreams/{sample_dream.dream_id}",
            files={"file": jpeg_file()},
        )
        assert resp.status_code == 403

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_admin_can_upload_to_any_dream(self, mock_upload, client, admin_user, sample_dream):
        mock_upload.return_value = {"secure_url": FAKE_URL}
        login(client, "admin@test.com", "admin123")
        resp = client.post(
            f"/images/dreams/{sample_dream.dream_id}",
            files={"file": jpeg_file()},
        )
        assert resp.status_code == 200

    @patch("app.routers.image_upload.cloudinary.uploader.upload")
    def test_dream_not_found(self, mock_upload, client, regular_user):
        login(client, "user@test.com", "user1234")
        resp = client.post(
            "/images/dreams/nonexistent",
            files={"file": jpeg_file()},
        )
        assert resp.status_code == 404

    def test_requires_auth(self, client, sample_dream):
        resp = client.post(
            f"/images/dreams/{sample_dream.dream_id}",
            files={"file": jpeg_file()},
        )
        assert resp.status_code == 401
