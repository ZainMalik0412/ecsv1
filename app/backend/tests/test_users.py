"""Tests for user management endpoints."""

import pytest


def test_list_users_as_admin(client, admin_token, student_user, lecturer_user):
    """Test listing users as admin."""
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # At least student and lecturer


def test_list_users_as_student_forbidden(client, student_token):
    """Test that students cannot list users."""
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


def test_create_user(client, admin_token):
    """Test creating a new user."""
    response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "newuser",
            "password": "password123",
            "full_name": "New User",
            "email": "new@test.com",
            "role": "student",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["role"] == "student"


def test_create_user_duplicate_username(client, admin_token, student_user):
    """Test creating user with duplicate username."""
    response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "student",  # Already exists
            "password": "password123",
            "full_name": "Another Student",
            "role": "student",
        },
    )
    assert response.status_code == 400


def test_get_user(client, admin_token, student_user):
    """Test getting a specific user."""
    response = client.get(
        f"/api/users/{student_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_user.id
    assert data["username"] == "student"


def test_update_user(client, admin_token, student_user):
    """Test updating a user."""
    response = client.patch(
        f"/api/users/{student_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


def test_delete_user(client, admin_token, test_db):
    """Test deleting a user."""
    from app.models import User, Role
    from app.auth import hash_password
    
    user = User(
        username="todelete",
        full_name="To Delete",
        role=Role.STUDENT,
        hashed_password=hash_password("password"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    response = client.delete(
        f"/api/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204
