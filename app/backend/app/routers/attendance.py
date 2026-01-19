"""Attendance management endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.deps import CurrentUser, DBSession, RequireLecturer
from app.models import Attendance, AttendanceStatus, Role, Session, SessionStatus, User
from app.schemas import AttendanceDetail, AttendanceOut, AttendanceUpdate, UserOut

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/session/{session_id}", response_model=List[AttendanceDetail])
def list_session_attendance(session_id: int, db: DBSession, current_user: CurrentUser):
    """List all attendance records for a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Authorization
    if current_user.role == Role.STUDENT:
        enrolled_module_ids = [m.id for m in current_user.enrolled_modules]
        if session.module_id not in enrolled_module_ids:
            raise HTTPException(status_code=403, detail="Not enrolled in this module")
    elif current_user.role == Role.LECTURER:
        if session.module.lecturer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not assigned to this module")
    attendances = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    result = []
    for a in attendances:
        student_out = UserOut(
            id=a.student.id,
            username=a.student.username,
            email=a.student.email,
            full_name=a.student.full_name,
            role=a.student.role,
            is_active=a.student.is_active,
            created_at=a.student.created_at,
            has_face_registered=len(a.student.face_encodings) > 0,
        )
        result.append(AttendanceDetail(
            id=a.id,
            session_id=a.session_id,
            student_id=a.student_id,
            status=a.status,
            marked_at=a.marked_at,
            face_confidence=a.face_confidence,
            notes=a.notes,
            student=student_out,
        ))
    return result


@router.get("/student/{student_id}", response_model=List[AttendanceOut])
def list_student_attendance(
    student_id: int,
    db: DBSession,
    current_user: CurrentUser,
    module_id: Optional[int] = Query(None),
):
    """List attendance records for a specific student."""
    # Students can only view their own attendance
    if current_user.role == Role.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Cannot view other student's attendance")
    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    if module_id:
        query = query.join(Session).filter(Session.module_id == module_id)
    attendances = query.all()
    return [AttendanceOut.model_validate(a) for a in attendances]


@router.get("/my", response_model=List[AttendanceOut])
def get_my_attendance(db: DBSession, current_user: CurrentUser):
    """Get current user's attendance records (for students)."""
    if current_user.role != Role.STUDENT:
        raise HTTPException(status_code=400, detail="Only students have attendance records")
    attendances = db.query(Attendance).filter(Attendance.student_id == current_user.id).all()
    return [AttendanceOut.model_validate(a) for a in attendances]


@router.patch("/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: DBSession,
    current_user: RequireLecturer,
):
    """Manually update an attendance record (Lecturer/Admin only)."""
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    # Check lecturer is assigned to this module
    if current_user.role == Role.LECTURER:
        if attendance.session.module.lecturer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not assigned to this module")
    if payload.status is not None:
        attendance.status = payload.status
        if payload.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
            attendance.marked_at = datetime.utcnow()
    if payload.notes is not None:
        attendance.notes = payload.notes
    db.commit()
    db.refresh(attendance)
    return AttendanceOut.model_validate(attendance)


@router.post("/mark-manual", response_model=AttendanceOut)
def mark_attendance_manual(
    session_id: int,
    student_id: int,
    attendance_status: AttendanceStatus,
    db: DBSession,
    current_user: RequireLecturer,
):
    """Manually mark a student's attendance for a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if session.status not in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Session is not active")
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == student_id
    ).first()
    if not attendance:
        # Create new attendance record
        student = db.query(User).filter(User.id == student_id, User.role == Role.STUDENT).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        attendance = Attendance(
            session_id=session_id,
            student_id=student_id,
            status=attendance_status,
            marked_at=datetime.utcnow() if attendance_status != AttendanceStatus.ABSENT else None,
        )
        db.add(attendance)
    else:
        attendance.status = attendance_status
        attendance.marked_at = datetime.utcnow() if attendance_status != AttendanceStatus.ABSENT else None
    db.commit()
    db.refresh(attendance)
    return AttendanceOut.model_validate(attendance)
