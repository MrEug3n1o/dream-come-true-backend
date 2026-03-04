"""
Shared pytest fixtures for the Dream Maker test suite.

Key design decisions:
- Sets APP_ENV=test and DATABASE_URL to a file SQLite BEFORE importing app,
  so main.py never tries to connect to Postgres at import time.
- Uses a single shared engine for both the app and fixtures (same file).
- Recreates all tables before each test for full isolation.
"""
import os
import pytest

# ── Must set env vars BEFORE any app imports ─────────────────────────────────
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_dreammaker.db"
os.environ["SECRET_KEY"] = "test-secret-key"

# ── Now safe to import app ────────────────────────────────────────────────────
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.database import Base, get_db
from app.models.models import User, Dream, UserRole, PersonType, ParticipationFormat
from app.auth import hash_password

# ── Test DB engine (same URL the app will use thanks to env override) ─────────
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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables before every test for full isolation."""
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


# ── User factories ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    user = User(
        full_name="Admin User",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def donor_user(db):
    user = User(
        full_name="Donor User",
        email="donor@test.com",
        password_hash=hash_password("donor123"),
        role=UserRole.DONOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def dreamer_user(db):
    user = User(
        full_name="Child Dreamer",
        email="dreamer@test.com",
        password_hash=hash_password("dream123"),
        role=UserRole.DREAMER,
        person_type=PersonType.CHILD,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_dream(db, dreamer_user):
    dream = Dream(
        dreamer_id=dreamer_user.user_id,
        title="Learn Piano Online",
        description="A child who dreams of learning piano.",
        participation_format=ParticipationFormat.ONLINE,
        target_budget=100.00,
        is_completed=False,
    )
    db.add(dream)
    db.commit()
    db.refresh(dream)
    return dream


@pytest.fixture
def completed_dream(db, dreamer_user):
    dream = Dream(
        dreamer_id=dreamer_user.user_id,
        title="Already Fulfilled Dream",
        description="This dream was already completed.",
        participation_format=ParticipationFormat.OFFLINE,
        target_budget=50.00,
        is_completed=True,
    )
    db.add(dream)
    db.commit()
    db.refresh(dream)
    return dream


# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


def auth_headers(client: TestClient, email: str, password: str) -> dict:
    return {"Authorization": f"Bearer {get_token(client, email, password)}"}
