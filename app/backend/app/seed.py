"""Seed database with demo data."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import AttendanceStatus, Module, Role, Session as AttendanceSession, SessionStatus, User, Attendance

logger = logging.getLogger(__name__)


def seed_demo_data(db: Session) -> None:
    """Seed the database with demo users, modules, and sessions."""
    
    # Check if already seeded
    if db.query(User).filter(User.username == "admin").first():
        logger.info("Database already seeded, skipping")
        return
    
    logger.info("Seeding demo data...")
    
    # Create demo users
    admin = User(
        username="admin",
        email="admin@example.com",
        full_name="System Administrator",
        role=Role.ADMIN,
        hashed_password=hash_password("admin"),
    )
    
    lecturer1 = User(
        username="lecturer",
        email="lecturer@example.com",
        full_name="Dr. Jane Smith",
        role=Role.LECTURER,
        hashed_password=hash_password("lecturer"),
    )
    
    lecturer2 = User(
        username="lecturer2",
        email="lecturer2@example.com",
        full_name="Prof. John Brown",
        role=Role.LECTURER,
        hashed_password=hash_password("lecturer2"),
    )
    
    student1 = User(
        username="student",
        email="student@example.com",
        full_name="Alice Johnson",
        role=Role.STUDENT,
        hashed_password=hash_password("student"),
    )
    
    student2 = User(
        username="student2",
        email="student2@example.com",
        full_name="Bob Williams",
        role=Role.STUDENT,
        hashed_password=hash_password("student2"),
    )
    
    student3 = User(
        username="student3",
        email="student3@example.com",
        full_name="Charlie Davis",
        role=Role.STUDENT,
        hashed_password=hash_password("student3"),
    )
    
    db.add_all([admin, lecturer1, lecturer2, student1, student2, student3])
    db.flush()
    
    # Create modules
    module1 = Module(
        code="CS101",
        name="Introduction to Computer Science",
        description="Fundamental concepts of computer science and programming.",
        lecturer_id=lecturer1.id,
    )
    
    module2 = Module(
        code="CS201",
        name="Data Structures and Algorithms",
        description="Advanced data structures and algorithm design.",
        lecturer_id=lecturer1.id,
    )
    
    module3 = Module(
        code="CS301",
        name="Database Systems",
        description="Relational databases, SQL, and database design.",
        lecturer_id=lecturer2.id,
    )
    
    db.add_all([module1, module2, module3])
    db.flush()
    
    # Enrol students
    module1.enrolled_students.extend([student1, student2, student3])
    module2.enrolled_students.extend([student1, student2])
    module3.enrolled_students.extend([student2, student3])
    
    db.flush()
    
    # Create sessions
    now = datetime.utcnow()
    
    # Past session (ended)
    session1 = AttendanceSession(
        module_id=module1.id,
        title="Week 1: Introduction",
        scheduled_start=now - timedelta(days=7),
        scheduled_end=now - timedelta(days=7) + timedelta(hours=2),
        actual_start=now - timedelta(days=7),
        actual_end=now - timedelta(days=7) + timedelta(hours=2),
        status=SessionStatus.ENDED,
    )
    
    # Today's session (scheduled)
    session2 = AttendanceSession(
        module_id=module1.id,
        title="Week 2: Variables and Types",
        scheduled_start=now + timedelta(hours=2),
        scheduled_end=now + timedelta(hours=4),
        status=SessionStatus.SCHEDULED,
    )
    
    # Active session
    session3 = AttendanceSession(
        module_id=module2.id,
        title="Arrays and Linked Lists",
        scheduled_start=now - timedelta(minutes=30),
        scheduled_end=now + timedelta(hours=1, minutes=30),
        actual_start=now - timedelta(minutes=30),
        status=SessionStatus.ACTIVE,
    )
    
    # Future session
    session4 = AttendanceSession(
        module_id=module3.id,
        title="SQL Fundamentals",
        scheduled_start=now + timedelta(days=1),
        scheduled_end=now + timedelta(days=1, hours=2),
        status=SessionStatus.SCHEDULED,
    )
    
    db.add_all([session1, session2, session3, session4])
    db.flush()
    
    # Create attendance records for past session
    attendance1 = Attendance(
        session_id=session1.id,
        student_id=student1.id,
        status=AttendanceStatus.PRESENT,
        marked_at=session1.actual_start + timedelta(minutes=5),
    )
    attendance2 = Attendance(
        session_id=session1.id,
        student_id=student2.id,
        status=AttendanceStatus.LATE,
        marked_at=session1.actual_start + timedelta(minutes=20),
    )
    attendance3 = Attendance(
        session_id=session1.id,
        student_id=student3.id,
        status=AttendanceStatus.ABSENT,
    )
    
    # Attendance for active session
    attendance4 = Attendance(
        session_id=session3.id,
        student_id=student1.id,
        status=AttendanceStatus.PRESENT,
        marked_at=session3.actual_start + timedelta(minutes=2),
    )
    attendance5 = Attendance(
        session_id=session3.id,
        student_id=student2.id,
        status=AttendanceStatus.ABSENT,
    )
    
    db.add_all([attendance1, attendance2, attendance3, attendance4, attendance5])
    
    db.commit()
    logger.info("Demo data seeded successfully")
