import os
import pytest

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_dreammaker.db"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.database import Base, get_db
from app.models.models import User, Dream, UserRole, PersonType, ParticipationFormat, DEFAULT_DREAM_IMAGE
from app.auth import hash_password

TEST_DB_URL = "sqlite:///./test_dreammaker.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ─── User factories ───────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    user = User(
        full_name="Admin User",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


@pytest.fixture
def regular_user(db):
    user = User(
        full_name="Regular User",
        email="user@test.com",
        password_hash=hash_password("user1234"),
        role=UserRole.USER,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


@pytest.fixture
def another_user(db):
    user = User(
        full_name="Another User",
        email="another@test.com",
        password_hash=hash_password("another123"),
        role=UserRole.USER,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


@pytest.fixture
def sample_dream(db, regular_user):
    dream = Dream(
        owner_id=regular_user.user_id,
        title="Learn Piano Online",
        description="A child who dreams of learning piano.",
        person_type=PersonType.CHILD,
        participation_format=ParticipationFormat.ONLINE,
        target_budget=100.00,
        city="Kyiv",
        image_url=DEFAULT_DREAM_IMAGE,
        is_completed=False,
    )
    db.add(dream); db.commit(); db.refresh(dream)
    return dream


@pytest.fixture
def completed_dream(db, regular_user):
    dream = Dream(
        owner_id=regular_user.user_id,
        title="Already Fulfilled Dream",
        description="This dream was already completed.",
        person_type=PersonType.ELDERLY,
        participation_format=ParticipationFormat.OFFLINE,
        target_budget=50.00,
        city="Lviv",
        image_url=DEFAULT_DREAM_IMAGE,
        is_completed=True,
    )
    db.add(dream); db.commit(); db.refresh(dream)
    return dream


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


def auth_headers(client: TestClient, email: str, password: str) -> dict:
    return {"Authorization": f"Bearer {get_token(client, email, password)}"}
