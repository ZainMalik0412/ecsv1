"""Tests for live session and recognition endpoints (FR6-FR8, FR14)."""

import base64
import pytest
from datetime import datetime, timedelta

from app.models import Attendance, AttendanceStatus, FaceEncoding, Module, Role, Session, SessionStatus, User


@pytest.fixture
def enrolled_student(test_db, test_module):
    """Create a student enrolled in the test module."""
    student = User(
        username="enrolled_student",
        email="enrolled@test.com",
        full_name="Enrolled Student",
        role=Role.STUDENT,
        hashed_password="hashed",
    )
    test_db.add(student)
    test_db.commit()
    test_db.refresh(student)
    test_module.enrolled_students.append(student)
    test_db.commit()
    return student


@pytest.fixture
def student_with_face(test_db, enrolled_student):
    """Create a student with a registered face encoding."""
    import numpy as np
    encoding = np.random.rand(128).astype(np.float32)
    face = FaceEncoding(
        user_id=enrolled_student.id,
        encoding=encoding.tobytes(),
    )
    test_db.add(face)
    test_db.commit()
    return enrolled_student


@pytest.fixture
def active_session(test_db, test_module):
    """Create an active session."""
    session = Session(
        module_id=test_module.id,
        title="Live Test Session",
        scheduled_start=datetime.utcnow() - timedelta(minutes=10),
        scheduled_end=datetime.utcnow() + timedelta(hours=1),
        status=SessionStatus.ACTIVE,
        actual_start=datetime.utcnow() - timedelta(minutes=10),
        late_threshold_minutes=15,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def paused_session(test_db, test_module):
    """Create a paused session."""
    session = Session(
        module_id=test_module.id,
        title="Paused Test Session",
        scheduled_start=datetime.utcnow() - timedelta(minutes=10),
        scheduled_end=datetime.utcnow() + timedelta(hours=1),
        status=SessionStatus.PAUSED,
        actual_start=datetime.utcnow() - timedelta(minutes=10),
        late_threshold_minutes=15,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


class TestLiveSessionState:
    """Tests for GET /sessions/{id}/live-state endpoint."""

    def test_get_live_state_as_lecturer(self, client, lecturer_token, active_session, enrolled_student):
        """Lecturer can get live session state."""
        response = client.get(
            f"/api/sessions/{active_session.id}/live-state",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == active_session.id
        assert data["status"] == "active"
        assert data["title"] == "Live Test Session"
        assert data["total_enrolled"] == 1
        assert data["present_count"] == 0
        assert data["late_count"] == 0
        assert data["absent_count"] == 0

    def test_get_live_state_not_found(self, client, lecturer_token):
        """Returns 404 for non-existent session."""
        response = client.get(
            "/api/sessions/9999/live-state",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 404

    def test_student_cannot_access_live_state(self, client, student_token, active_session):
        """Students cannot access live session state."""
        response = client.get(
            f"/api/sessions/{active_session.id}/live-state",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 403


class TestLiveAttendance:
    """Tests for GET /sessions/{id}/live-attendance endpoint."""

    def test_get_live_attendance_empty(self, client, lecturer_token, active_session):
        """Returns empty list when no attendance records."""
        response = client.get(
            f"/api/sessions/{active_session.id}/live-attendance",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == active_session.id
        assert data["students"] == []

    def test_get_live_attendance_with_records(self, client, lecturer_token, active_session, enrolled_student, test_db):
        """Returns attendance records when present."""
        attendance = Attendance(
            session_id=active_session.id,
            student_id=enrolled_student.id,
            status=AttendanceStatus.PRESENT,
            marked_at=datetime.utcnow(),
            face_confidence=0.95,
        )
        test_db.add(attendance)
        test_db.commit()

        response = client.get(
            f"/api/sessions/{active_session.id}/live-attendance",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["students"]) == 1
        assert data["students"][0]["student_name"] == "Enrolled Student"
        assert data["students"][0]["status"] == "present"
        assert data["students"][0]["face_confidence"] == 0.95


class TestRecognizeFrame:
    """Tests for POST /sessions/{id}/recognize-frame endpoint."""

    def test_recognize_frame_paused_session(self, client, lecturer_token, paused_session):
        """Recognition is paused when session is paused (FR14)."""
        # Create a minimal valid image
        dummy_image = base64.b64encode(b"fake_image_data").decode()
        
        response = client.post(
            f"/api/sessions/{paused_session.id}/recognize-frame",
            headers={"Authorization": f"Bearer {lecturer_token}"},
            json={"image_base64": dummy_image},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["frame_processed"] is False
        assert "paused" in data["message"].lower()

    def test_recognize_frame_scheduled_session(self, client, lecturer_token, test_module, test_db):
        """Cannot recognize frames for non-active session."""
        session = Session(
            module_id=test_module.id,
            title="Scheduled Session",
            scheduled_start=datetime.utcnow() + timedelta(hours=1),
            scheduled_end=datetime.utcnow() + timedelta(hours=2),
            status=SessionStatus.SCHEDULED,
        )
        test_db.add(session)
        test_db.commit()
        
        dummy_image = base64.b64encode(b"fake_image_data").decode()
        
        response = client.post(
            f"/api/sessions/{session.id}/recognize-frame",
            headers={"Authorization": f"Bearer {lecturer_token}"},
            json={"image_base64": dummy_image},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["frame_processed"] is False

    def test_student_cannot_recognize_frame(self, client, student_token, active_session):
        """Students cannot call recognize-frame endpoint."""
        dummy_image = base64.b64encode(b"fake_image_data").decode()
        
        response = client.post(
            f"/api/sessions/{active_session.id}/recognize-frame",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"image_base64": dummy_image},
        )
        assert response.status_code == 403


class TestSessionPauseResume:
    """Tests for session pause/resume functionality (FR14)."""

    def test_pause_active_session(self, client, lecturer_token, active_session):
        """Lecturer can pause an active session."""
        response = client.post(
            f"/api/sessions/{active_session.id}/pause",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    def test_resume_paused_session(self, client, lecturer_token, paused_session):
        """Lecturer can resume a paused session."""
        response = client.post(
            f"/api/sessions/{paused_session.id}/resume",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_cannot_pause_ended_session(self, client, lecturer_token, test_module, test_db):
        """Cannot pause an ended session."""
        session = Session(
            module_id=test_module.id,
            title="Ended Session",
            scheduled_start=datetime.utcnow() - timedelta(hours=2),
            scheduled_end=datetime.utcnow() - timedelta(hours=1),
            status=SessionStatus.ENDED,
            actual_start=datetime.utcnow() - timedelta(hours=2),
            actual_end=datetime.utcnow() - timedelta(hours=1),
        )
        test_db.add(session)
        test_db.commit()
        
        response = client.post(
            f"/api/sessions/{session.id}/pause",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 400
