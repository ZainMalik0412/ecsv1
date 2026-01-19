"""Session management endpoints."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DBSession, RequireLecturer
from app.models import Attendance, AttendanceStatus, FaceEncoding, Module, Role, Session, SessionStatus
from app.schemas import (
    SessionCreate, SessionDetail, SessionOut, SessionUpdate, ModuleOut,
    LiveRecognitionRequest, LiveRecognitionResponse, RecognizedStudent,
    LiveSessionState, LiveAttendanceList, LiveAttendanceStudent,
)
from app.services.face_recognition import (
    bytes_to_encoding, extract_all_faces, match_face_to_students,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=List[SessionOut])
def list_sessions(
    db: DBSession,
    current_user: CurrentUser,
    module_id: Optional[int] = Query(None),
    status_filter: Optional[SessionStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
):
    """List sessions. Filtered by user role and optionally by module or status."""
    query = db.query(Session)
    if current_user.role == Role.STUDENT:
        # Students see sessions for modules they're enrolled in
        enrolled_module_ids = [m.id for m in current_user.enrolled_modules]
        query = query.filter(Session.module_id.in_(enrolled_module_ids))
    elif current_user.role == Role.LECTURER:
        # Lecturers see sessions for modules they teach
        taught_module_ids = [m.id for m in current_user.taught_modules]
        query = query.filter(Session.module_id.in_(taught_module_ids))
    if module_id:
        query = query.filter(Session.module_id == module_id)
    if status_filter:
        query = query.filter(Session.status == status_filter)
    sessions = query.order_by(Session.scheduled_start.desc()).offset(skip).limit(limit).all()
    return [SessionOut.model_validate(s) for s in sessions]


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DBSession, current_user: RequireLecturer):
    """Create a new session for a module."""
    module = db.query(Module).filter(Module.id == payload.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    if current_user.role == Role.LECTURER and module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if payload.scheduled_end <= payload.scheduled_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    session = Session(
        module_id=payload.module_id,
        title=payload.title,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        late_threshold_minutes=payload.late_threshold_minutes,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: int, db: DBSession, current_user: CurrentUser):
    """Get session details."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Authorization check
    if current_user.role == Role.STUDENT:
        enrolled_module_ids = [m.id for m in current_user.enrolled_modules]
        if session.module_id not in enrolled_module_ids:
            raise HTTPException(status_code=403, detail="Not enrolled in this module")
    elif current_user.role == Role.LECTURER:
        if session.module.lecturer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not assigned to this module")
    present_count = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
    ).count()
    return SessionDetail(
        id=session.id,
        module_id=session.module_id,
        title=session.title,
        scheduled_start=session.scheduled_start,
        scheduled_end=session.scheduled_end,
        late_threshold_minutes=session.late_threshold_minutes,
        status=session.status,
        actual_start=session.actual_start,
        actual_end=session.actual_end,
        created_at=session.created_at,
        module=ModuleOut.model_validate(session.module) if session.module else None,
        attendance_count=len(session.attendances),
        present_count=present_count,
    )


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(session_id: int, payload: SessionUpdate, db: DBSession, current_user: RequireLecturer):
    """Update a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if payload.title is not None:
        session.title = payload.title
    if payload.scheduled_start is not None:
        session.scheduled_start = payload.scheduled_start
    if payload.scheduled_end is not None:
        session.scheduled_end = payload.scheduled_end
    if payload.late_threshold_minutes is not None:
        session.late_threshold_minutes = payload.late_threshold_minutes
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: DBSession, current_user: RequireLecturer):
    """Delete a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    db.delete(session)
    db.commit()


@router.post("/{session_id}/start", response_model=SessionOut)
def start_session(session_id: int, db: DBSession, current_user: RequireLecturer):
    """Start a session and create attendance records for enrolled students."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if session.status != SessionStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Cannot start session with status {session.status.value}")
    session.status = SessionStatus.ACTIVE
    session.actual_start = datetime.utcnow()
    # Create attendance records for all enrolled students (default ABSENT)
    for student in session.module.enrolled_students:
        existing = db.query(Attendance).filter(
            Attendance.session_id == session_id,
            Attendance.student_id == student.id
        ).first()
        if not existing:
            attendance = Attendance(
                session_id=session_id,
                student_id=student.id,
                status=AttendanceStatus.ABSENT,
            )
            db.add(attendance)
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.post("/{session_id}/pause", response_model=SessionOut)
def pause_session(session_id: int, db: DBSession, current_user: RequireLecturer):
    """Pause an active session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Can only pause an active session")
    session.status = SessionStatus.PAUSED
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.post("/{session_id}/resume", response_model=SessionOut)
def resume_session(session_id: int, db: DBSession, current_user: RequireLecturer):
    """Resume a paused session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if session.status != SessionStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Can only resume a paused session")
    session.status = SessionStatus.ACTIVE
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.post("/{session_id}/end", response_model=SessionOut)
def end_session(session_id: int, db: DBSession, current_user: RequireLecturer):
    """End a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    if session.status not in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Can only end an active or paused session")
    session.status = SessionStatus.ENDED
    session.actual_end = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


# ─────────────────────────────────────────────────────────────────────────────
# Live Recognition Endpoints (FR6-FR8)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{session_id}/live-state", response_model=LiveSessionState)
def get_live_session_state(session_id: int, db: DBSession, current_user: RequireLecturer):
    """Get the current state of a live session for the live attendance UI."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    
    # Count attendance by status
    present_count = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.status == AttendanceStatus.PRESENT
    ).count()
    late_count = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.status == AttendanceStatus.LATE
    ).count()
    absent_count = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.status == AttendanceStatus.ABSENT
    ).count()
    
    return LiveSessionState(
        session_id=session.id,
        status=session.status,
        title=session.title,
        module_code=session.module.code,
        module_name=session.module.name,
        actual_start=session.actual_start,
        total_enrolled=len(session.module.enrolled_students),
        present_count=present_count,
        late_count=late_count,
        absent_count=absent_count,
    )


@router.get("/{session_id}/live-attendance", response_model=LiveAttendanceList)
def get_live_attendance(session_id: int, db: DBSession, current_user: RequireLecturer):
    """Get the live attendance list for a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    
    attendances = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    
    students = []
    for a in attendances:
        students.append(LiveAttendanceStudent(
            student_id=a.student.id,
            student_name=a.student.full_name,
            username=a.student.username,
            status=a.status,
            marked_at=a.marked_at,
            face_confidence=a.face_confidence,
            has_face_registered=len(a.student.face_encodings) > 0,
        ))
    
    # Sort: present first, then late, then absent
    status_order = {AttendanceStatus.PRESENT: 0, AttendanceStatus.LATE: 1, AttendanceStatus.ABSENT: 2}
    students.sort(key=lambda s: (status_order.get(s.status, 3), s.student_name))
    
    return LiveAttendanceList(session_id=session_id, students=students)


@router.post("/{session_id}/recognize-frame", response_model=LiveRecognitionResponse)
def recognize_frame(
    session_id: int,
    payload: LiveRecognitionRequest,
    db: DBSession,
    current_user: RequireLecturer,
):
    """
    Process a camera frame and recognize faces against enrolled students.
    
    This endpoint:
    1. Validates the session is active (not paused or ended)
    2. Extracts faces from the frame
    3. Matches each face against enrolled students' face templates
    4. Marks attendance for matched students (with cooldown to prevent duplicates)
    5. Returns list of recognized students
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.LECTURER and session.module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    
    # Only process frames when session is active (not paused)
    if session.status == SessionStatus.PAUSED:
        return LiveRecognitionResponse(
            success=True,
            message="Session is paused - recognition paused",
            frame_processed=False,
        )
    
    if session.status != SessionStatus.ACTIVE:
        return LiveRecognitionResponse(
            success=False,
            message=f"Session is not active (status: {session.status.value})",
            frame_processed=False,
        )
    
    # Extract faces from frame
    try:
        face_encodings, message = extract_all_faces(payload.image_base64)
    except Exception as e:
        return LiveRecognitionResponse(
            success=False,
            message=f"Face extraction failed: {str(e)}",
            frame_processed=False,
        )
    
    if not face_encodings:
        return LiveRecognitionResponse(
            success=True,
            message=message,
            frame_processed=True,
        )
    
    # Get all enrolled students with their face encodings
    enrolled_students = session.module.enrolled_students
    student_encoding_data = []
    for student in enrolled_students:
        encodings = [bytes_to_encoding(fe.encoding) for fe in student.face_encodings]
        if encodings:
            student_encoding_data.append((student.id, student.full_name, encodings))
    
    if not student_encoding_data:
        return LiveRecognitionResponse(
            success=True,
            message="No students with registered faces in this module",
            frame_processed=True,
        )
    
    # Match faces and update attendance
    recognized = []
    now = datetime.utcnow()
    late_threshold = session.actual_start + timedelta(minutes=session.late_threshold_minutes)
    
    for face_encoding in face_encodings:
        match = match_face_to_students(face_encoding, student_encoding_data)
        if match:
            student_id, student_name, confidence = match
            
            # Get or create attendance record
            attendance = db.query(Attendance).filter(
                Attendance.session_id == session_id,
                Attendance.student_id == student_id
            ).first()
            
            already_marked = False
            if attendance:
                # Check if already marked present/late (idempotency)
                if attendance.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
                    already_marked = True
                else:
                    # Update from absent to present/late
                    attendance.status = AttendanceStatus.LATE if now > late_threshold else AttendanceStatus.PRESENT
                    attendance.marked_at = now
                    attendance.face_confidence = confidence
            else:
                # Create new record
                status = AttendanceStatus.LATE if now > late_threshold else AttendanceStatus.PRESENT
                attendance = Attendance(
                    session_id=session_id,
                    student_id=student_id,
                    status=status,
                    marked_at=now,
                    face_confidence=confidence,
                )
                db.add(attendance)
            
            recognized.append(RecognizedStudent(
                student_id=student_id,
                student_name=student_name,
                confidence=confidence,
                status=attendance.status,
                already_marked=already_marked,
            ))
    
    db.commit()
    
    return LiveRecognitionResponse(
        success=True,
        message=f"Processed frame, recognized {len(recognized)} student(s)",
        recognized_students=recognized,
        frame_processed=True,
    )
