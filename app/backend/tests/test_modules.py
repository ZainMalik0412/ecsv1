"""Tests for module management endpoints."""

import pytest


def test_list_modules_as_admin(client, admin_token, test_module):
    """Test listing modules as admin."""
    response = client.get(
        "/api/modules",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_create_module(client, admin_token, lecturer_user):
    """Test creating a module."""
    response = client.post(
        "/api/modules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": "CS202",
            "name": "Advanced Programming",
            "description": "Advanced topics",
            "lecturer_id": lecturer_user.id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "CS202"
    assert data["name"] == "Advanced Programming"


def test_create_module_duplicate_code(client, admin_token, test_module):
    """Test creating module with duplicate code."""
    response = client.post(
        "/api/modules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": "CS101",  # Already exists
            "name": "Another Module",
        },
    )
    assert response.status_code == 400


def test_get_module(client, admin_token, test_module):
    """Test getting a specific module."""
    response = client.get(
        f"/api/modules/{test_module.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_module.id
    assert data["code"] == "CS101"


def test_update_module(client, admin_token, test_module):
    """Test updating a module."""
    response = client.patch(
        f"/api/modules/{test_module.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Updated Module Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Module Name"


def test_delete_module(client, admin_token, test_module):
    """Test deleting a module."""
    response = client.delete(
        f"/api/modules/{test_module.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_lecturer_cannot_create_module(client, lecturer_token):
    """Test that lecturers cannot create modules."""
    response = client.post(
        "/api/modules",
        headers={"Authorization": f"Bearer {lecturer_token}"},
        json={
            "code": "CS303",
            "name": "New Module",
        },
    )
    assert response.status_code == 403
