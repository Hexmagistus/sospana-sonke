"""Pytest fixtures: isolated in-memory database and API test client."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sospana.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import session as db_session
from app.db.base import Base
from app.main import app
from app.db.session import get_db


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path):
    """Point file storage at a per-test temp directory so uploads don't leak."""
    from app.services.storage import reset_storage_for_tests
    reset_storage_for_tests(str(tmp_path / "storage"))
    yield


@pytest.fixture()
def db_engine():
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db(db_engine):
    """A direct SQLAlchemy session for service-level (non-HTTP) tests."""
    S = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = S()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    # Point the app's engine/session at the test database and disable startup create_all.
    db_session.engine = db_engine
    db_session.SessionLocal = TestingSession
    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, email="thandi@example.com", password="Password123!"):
    reg = client.post("/api/v1/auth/register", json={
        "email": email, "password": password,
        "first_name": "Thandi", "last_name": "Mokoena", "mobile_number": "0821234567",
    })
    assert reg.status_code == 201, reg.text
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    return reg.json(), tokens


def make_admin(db_engine, email="admin@example.com", password="AdminPass123!"):
    from sqlalchemy.orm import sessionmaker
    from app.models.user import User
    from app.core import security
    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        u = User(email=email, password_hash=security.hash_password(password),
                 first_name="Admin", last_name="User", role="admin", email_verified=True)
        db.add(u)
        db.commit()
    finally:
        db.close()
    return email, password
