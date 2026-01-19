"""Tests for authentication endpoints."""

import pytest


def test_login_success(client, admin_user):
    """Test successful login."""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    """Test login with wrong password."""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    response = client.post(
        "/api/auth/login",
        data={"username": "nonexistent", "password": "password"},
    )
    assert response.status_code == 401


def test_get_me(client, admin_token):
    """Test get current user endpoint."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_get_me_no_token(client):
    """Test get current user without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client):
    """Test get current user with invalid token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401
