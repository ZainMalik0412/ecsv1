"""Pytest fixtures for testing."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.auth import hash_password
from app.models import User, Role, Module, Session as AttendanceSession, SessionStatus


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(test_db):
    """Create an admin user for testing."""
    user = User(
        username="admin",
        email="admin@test.com",
        full_name="Test Admin",
        role=Role.ADMIN,
        hashed_password=hash_password("admin123"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def lecturer_user(test_db):
    """Create a lecturer user for testing."""
    user = User(
        username="lecturer",
        email="lecturer@test.com",
        full_name="Test Lecturer",
        role=Role.LECTURER,
        hashed_password=hash_password("lecturer123"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def student_user(test_db):
    """Create a student user for testing."""
    user = User(
        username="student",
        email="student@test.com",
        full_name="Test Student",
        role=Role.STUDENT,
        hashed_password=hash_password("student123"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_module(test_db, lecturer_user):
    """Create a test module."""
    module = Module(
        code="CS101",
        name="Test Module",
        description="A test module",
        lecturer_id=lecturer_user.id,
    )
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)
    return module


@pytest.fixture
def admin_token(client, admin_user):
    """Get an auth token for admin user."""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def lecturer_token(client, lecturer_user):
    """Get an auth token for lecturer user."""
    response = client.post(
        "/api/auth/login",
        data={"username": "lecturer", "password": "lecturer123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def student_token(client, student_user):
    """Get an auth token for student user."""
    response = client.post(
        "/api/auth/login",
        data={"username": "student", "password": "student123"},
    )
    return response.json()["access_token"]
