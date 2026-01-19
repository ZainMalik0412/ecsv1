"""Tests for session management endpoints."""

import pytest
from datetime import datetime, timedelta


def test_create_session(client, lecturer_token, test_module):
    """Test creating a session."""
    start = datetime.utcnow() + timedelta(hours=1)
    end = start + timedelta(hours=2)
    
    response = client.post(
        "/api/sessions",
        headers={"Authorization": f"Bearer {lecturer_token}"},
        json={
            "module_id": test_module.id,
            "title": "Week 1 Lecture",
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
            "late_threshold_minutes": 15,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Week 1 Lecture"
    assert data["status"] == "scheduled"


def test_start_session(client, lecturer_token, test_module, test_db):
    """Test starting a session."""
    from app.models import Session, SessionStatus
    
    start = datetime.utcnow()
    end = start + timedelta(hours=2)
    
    session = Session(
        module_id=test_module.id,
        title="Test Session",
        scheduled_start=start,
        scheduled_end=end,
        status=SessionStatus.SCHEDULED,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    response = client.post(
        f"/api/sessions/{session.id}/start",
        headers={"Authorization": f"Bearer {lecturer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


def test_pause_session(client, lecturer_token, test_module, test_db):
    """Test pausing a session."""
    from app.models import Session, SessionStatus
    
    start = datetime.utcnow()
    end = start + timedelta(hours=2)
    
    session = Session(
        module_id=test_module.id,
        title="Active Session",
        scheduled_start=start,
        scheduled_end=end,
        status=SessionStatus.ACTIVE,
        actual_start=start,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    response = client.post(
        f"/api/sessions/{session.id}/pause",
        headers={"Authorization": f"Bearer {lecturer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"


def test_end_session(client, lecturer_token, test_module, test_db):
    """Test ending a session."""
    from app.models import Session, SessionStatus
    
    start = datetime.utcnow()
    end = start + timedelta(hours=2)
    
    session = Session(
        module_id=test_module.id,
        title="Active Session",
        scheduled_start=start,
        scheduled_end=end,
        status=SessionStatus.ACTIVE,
        actual_start=start,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    response = client.post(
        f"/api/sessions/{session.id}/end",
        headers={"Authorization": f"Bearer {lecturer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ended"


def test_student_cannot_start_session(client, student_token, test_module, test_db):
    """Test that students cannot start sessions."""
    from app.models import Session, SessionStatus
    
    start = datetime.utcnow()
    end = start + timedelta(hours=2)
    
    session = Session(
        module_id=test_module.id,
        title="Test Session",
        scheduled_start=start,
        scheduled_end=end,
        status=SessionStatus.SCHEDULED,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    response = client.post(
        f"/api/sessions/{session.id}/start",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403
