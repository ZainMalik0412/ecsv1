"""Tests for student statistics endpoint (FR11)."""

import pytest
from datetime import datetime, timedelta

from app.models import Attendance, AttendanceStatus, Module, Role, Session, SessionStatus, User


@pytest.fixture
def student_with_modules(test_db):
    """Create a student enrolled in multiple modules with attendance history."""
    # Create student
    student = User(
        username="stats_student",
        email="stats@test.com",
        full_name="Stats Student",
        role=Role.STUDENT,
        hashed_password="hashed",
    )
    test_db.add(student)
    test_db.commit()
    
    # Create lecturer
    lecturer = User(
        username="stats_lecturer",
        email="lecturer@test.com",
        full_name="Stats Lecturer",
        role=Role.LECTURER,
        hashed_password="hashed",
    )
    test_db.add(lecturer)
    test_db.commit()
    
    # Create modules
    module1 = Module(
        code="STAT101",
        name="Statistics 101",
        lecturer_id=lecturer.id,
    )
    module2 = Module(
        code="STAT102",
        name="Statistics 102",
        lecturer_id=lecturer.id,
    )
    test_db.add_all([module1, module2])
    test_db.commit()
    
    # Enroll student
    module1.enrolled_students.append(student)
    module2.enrolled_students.append(student)
    test_db.commit()
    
    # Create ended sessions with attendance
    sessions = []
    for i in range(3):
        session = Session(
            module_id=module1.id,
            title=f"Module 1 Session {i+1}",
            scheduled_start=datetime.utcnow() - timedelta(days=i+1),
            scheduled_end=datetime.utcnow() - timedelta(days=i+1) + timedelta(hours=1),
            status=SessionStatus.ENDED,
            actual_start=datetime.utcnow() - timedelta(days=i+1),
            actual_end=datetime.utcnow() - timedelta(days=i+1) + timedelta(hours=1),
        )
        sessions.append(session)
    
    for i in range(2):
        session = Session(
            module_id=module2.id,
            title=f"Module 2 Session {i+1}",
            scheduled_start=datetime.utcnow() - timedelta(days=i+1),
            scheduled_end=datetime.utcnow() - timedelta(days=i+1) + timedelta(hours=1),
            status=SessionStatus.ENDED,
            actual_start=datetime.utcnow() - timedelta(days=i+1),
            actual_end=datetime.utcnow() - timedelta(days=i+1) + timedelta(hours=1),
        )
        sessions.append(session)
    
    test_db.add_all(sessions)
    test_db.commit()
    
    # Add attendance records: 2 present, 1 late in module1; 1 present, 1 absent in module2
    attendances = [
        Attendance(session_id=sessions[0].id, student_id=student.id, status=AttendanceStatus.PRESENT, marked_at=datetime.utcnow()),
        Attendance(session_id=sessions[1].id, student_id=student.id, status=AttendanceStatus.PRESENT, marked_at=datetime.utcnow()),
        Attendance(session_id=sessions[2].id, student_id=student.id, status=AttendanceStatus.LATE, marked_at=datetime.utcnow()),
        Attendance(session_id=sessions[3].id, student_id=student.id, status=AttendanceStatus.PRESENT, marked_at=datetime.utcnow()),
        Attendance(session_id=sessions[4].id, student_id=student.id, status=AttendanceStatus.ABSENT),
    ]
    test_db.add_all(attendances)
    test_db.commit()
    
    return student


@pytest.fixture
def stats_student_token(client, student_with_modules):
    """Get auth token for stats student."""
    from app.auth import hash_password
    student_with_modules.hashed_password = hash_password("testpass")
    response = client.post(
        "/api/auth/login",
        data={"username": "stats_student", "password": "testpass"},
    )
    return response.json()["access_token"]


class TestStudentStatistics:
    """Tests for GET /dashboard/student-stats endpoint."""

    def test_get_student_stats(self, client, stats_student_token):
        """Student can get their attendance statistics."""
        response = client.get(
            "/api/dashboard/student-stats",
            headers={"Authorization": f"Bearer {stats_student_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check overall stats
        assert data["total_sessions"] == 5
        assert data["present_count"] == 3
        assert data["late_count"] == 1
        assert data["absent_count"] == 1
        # 4 out of 5 attended (present + late)
        assert data["overall_rate"] == 80.0
        
        # Check module stats
        assert len(data["modules"]) == 2

    def test_lecturer_cannot_access_student_stats(self, client, lecturer_token):
        """Lecturers cannot access student statistics endpoint."""
        response = client.get(
            "/api/dashboard/student-stats",
            headers={"Authorization": f"Bearer {lecturer_token}"},
        )
        assert response.status_code == 403

    def test_admin_cannot_access_student_stats(self, client, admin_token):
        """Admins cannot access student statistics endpoint."""
        response = client.get(
            "/api/dashboard/student-stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 403

    def test_student_with_no_modules(self, client, student_token):
        """Student with no enrolled modules gets empty stats."""
        response = client.get(
            "/api/dashboard/student-stats",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        assert data["overall_rate"] == 0.0
        assert len(data["modules"]) == 0
