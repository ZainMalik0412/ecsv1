"""Tests for user signup functionality."""

import pytest
from fastapi.testclient import TestClient

from app.models import User, Role


class TestSignup:
    """Test cases for the signup endpoint."""

    def test_signup_success(self, client: TestClient, test_db):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "newuser",
                "password": "password123",
                "full_name": "New User",
                "email": "newuser@example.com",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "student"
        assert data["is_active"] is True
        assert data["has_face_registered"] is False
        assert "id" in data
        assert "created_at" in data

    def test_signup_without_email(self, client: TestClient, test_db):
        """Test signup without providing email (optional field)."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "noemailuser",
                "password": "password123",
                "full_name": "No Email User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "noemailuser"
        assert data["email"] is None
        assert data["role"] == "student"

    def test_signup_duplicate_username(self, client: TestClient, test_db):
        """Test signup with duplicate username fails."""
        # First signup
        client.post(
            "/api/auth/signup",
            json={
                "username": "duplicateuser",
                "password": "password123",
                "full_name": "First User",
            },
        )
        # Second signup with same username
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "duplicateuser",
                "password": "password456",
                "full_name": "Second User",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Username already exists"

    def test_signup_duplicate_email(self, client: TestClient, test_db):
        """Test signup with duplicate email fails."""
        # First signup
        client.post(
            "/api/auth/signup",
            json={
                "username": "user1",
                "password": "password123",
                "full_name": "First User",
                "email": "duplicate@example.com",
            },
        )
        # Second signup with same email
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "user2",
                "password": "password456",
                "full_name": "Second User",
                "email": "duplicate@example.com",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already exists"

    def test_signup_short_username(self, client: TestClient, test_db):
        """Test signup with too short username fails validation."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "ab",
                "password": "password123",
                "full_name": "Short Username",
            },
        )
        assert response.status_code == 422

    def test_signup_short_password(self, client: TestClient, test_db):
        """Test signup with too short password fails validation."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "validuser",
                "password": "123",
                "full_name": "Short Password",
            },
        )
        assert response.status_code == 422

    def test_signup_empty_full_name(self, client: TestClient, test_db):
        """Test signup with empty full name fails validation."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "validuser",
                "password": "password123",
                "full_name": "",
            },
        )
        assert response.status_code == 422

    def test_signup_then_login(self, client: TestClient, test_db):
        """Test that a user can login after signing up."""
        # Signup
        signup_response = client.post(
            "/api/auth/signup",
            json={
                "username": "logintest",
                "password": "testpassword",
                "full_name": "Login Test User",
            },
        )
        assert signup_response.status_code == 201

        # Login
        login_response = client.post(
            "/api/auth/login",
            data={"username": "logintest", "password": "testpassword"},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    def test_signup_user_is_student_by_default(self, client: TestClient, test_db):
        """Test that new signups are always students regardless of role in request."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "studentuser",
                "password": "password123",
                "full_name": "Student User",
                "role": "admin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "student"

    def test_signup_creates_user_in_database(self, client: TestClient, test_db):
        """Test that signup actually creates a user in the database."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "dbcheckuser",
                "password": "password123",
                "full_name": "DB Check User",
            },
        )
        assert response.status_code == 201
        
        user = test_db.query(User).filter(User.username == "dbcheckuser").first()
        assert user is not None
        assert user.full_name == "DB Check User"
        assert user.role == Role.STUDENT
        assert user.is_active is True

    def test_signup_password_is_hashed(self, client: TestClient, test_db):
        """Test that the password is stored hashed, not in plaintext."""
        response = client.post(
            "/api/auth/signup",
            json={
                "username": "hashcheckuser",
                "password": "plaintextpassword",
                "full_name": "Hash Check User",
            },
        )
        assert response.status_code == 201
        
        user = test_db.query(User).filter(User.username == "hashcheckuser").first()
        assert user is not None
        assert user.hashed_password != "plaintextpassword"
        assert user.hashed_password.startswith("$2b$")
