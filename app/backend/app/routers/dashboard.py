"""Dashboard and reporting endpoints."""

import csv
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.deps import CurrentUser, DBSession, RequireLecturer
from app.models import Attendance, AttendanceStatus, Module, Role, Session, SessionStatus, User
from app.schemas import (
    AttendanceReportRow, DashboardStats, StudentAttendanceStats, ModuleAttendanceStats,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: DBSession, current_user: CurrentUser):
    """Get dashboard statistics."""
    if current_user.role == Role.ADMIN:
        total_students = db.query(User).filter(User.role == Role.STUDENT).count()
        total_lecturers = db.query(User).filter(User.role == Role.LECTURER).count()
        total_modules = db.query(Module).count()
        total_sessions = db.query(Session).count()
        active_sessions = db.query(Session).filter(Session.status == SessionStatus.ACTIVE).count()
        total_attendance = db.query(Attendance).count()
        present_attendance = db.query(Attendance).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
    elif current_user.role == Role.LECTURER:
        taught_module_ids = [m.id for m in current_user.taught_modules]
        total_students = db.query(User).join(User.enrolled_modules).filter(
            Module.id.in_(taught_module_ids)
        ).distinct().count()
        total_lecturers = 1
        total_modules = len(taught_module_ids)
        total_sessions = db.query(Session).filter(Session.module_id.in_(taught_module_ids)).count()
        active_sessions = db.query(Session).filter(
            Session.module_id.in_(taught_module_ids),
            Session.status == SessionStatus.ACTIVE
        ).count()
        total_attendance = db.query(Attendance).join(Session).filter(
            Session.module_id.in_(taught_module_ids)
        ).count()
        present_attendance = db.query(Attendance).join(Session).filter(
            Session.module_id.in_(taught_module_ids),
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
    else:  # STUDENT
        enrolled_module_ids = [m.id for m in current_user.enrolled_modules]
        total_students = 1
        total_lecturers = db.query(User).join(Module, Module.lecturer_id == User.id).filter(
            Module.id.in_(enrolled_module_ids)
        ).distinct().count()
        total_modules = len(enrolled_module_ids)
        total_sessions = db.query(Session).filter(Session.module_id.in_(enrolled_module_ids)).count()
        active_sessions = db.query(Session).filter(
            Session.module_id.in_(enrolled_module_ids),
            Session.status == SessionStatus.ACTIVE
        ).count()
        total_attendance = db.query(Attendance).filter(Attendance.student_id == current_user.id).count()
        present_attendance = db.query(Attendance).filter(
            Attendance.student_id == current_user.id,
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
    
    attendance_rate = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0.0
    
    return DashboardStats(
        total_students=total_students,
        total_lecturers=total_lecturers,
        total_modules=total_modules,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        attendance_rate=round(attendance_rate, 2),
    )


@router.get("/reports/attendance", response_model=List[AttendanceReportRow])
def get_attendance_report(
    db: DBSession,
    current_user: RequireLecturer,
    module_id: Optional[int] = Query(None),
    session_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    status_filter: Optional[AttendanceStatus] = Query(None, alias="status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = 0,
    limit: int = 500,
):
    """Generate attendance report with filters."""
    query = db.query(Attendance).join(Session).join(Module).join(
        User, Attendance.student_id == User.id
    )
    
    # Role-based filtering
    if current_user.role == Role.LECTURER:
        taught_module_ids = [m.id for m in current_user.taught_modules]
        query = query.filter(Module.id.in_(taught_module_ids))
    
    # Apply filters
    if module_id:
        query = query.filter(Module.id == module_id)
    if session_id:
        query = query.filter(Session.id == session_id)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)
    if date_from:
        query = query.filter(Session.scheduled_start >= date_from)
    if date_to:
        query = query.filter(Session.scheduled_start <= date_to)
    
    attendances = query.order_by(Session.scheduled_start.desc()).offset(skip).limit(limit).all()
    
    return [
        AttendanceReportRow(
            student_id=a.student.id,
            student_name=a.student.full_name,
            student_username=a.student.username,
            session_id=a.session.id,
            session_title=a.session.title,
            module_code=a.session.module.code,
            module_name=a.session.module.name,
            scheduled_start=a.session.scheduled_start,
            status=a.status,
            marked_at=a.marked_at,
        )
        for a in attendances
    ]


@router.get("/reports/attendance/csv")
def export_attendance_csv(
    db: DBSession,
    current_user: RequireLecturer,
    module_id: Optional[int] = Query(None),
    session_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """Export attendance report as CSV."""
    query = db.query(Attendance).join(Session).join(Module).join(
        User, Attendance.student_id == User.id
    )
    
    if current_user.role == Role.LECTURER:
        taught_module_ids = [m.id for m in current_user.taught_modules]
        query = query.filter(Module.id.in_(taught_module_ids))
    
    if module_id:
        query = query.filter(Module.id == module_id)
    if session_id:
        query = query.filter(Session.id == session_id)
    if date_from:
        query = query.filter(Session.scheduled_start >= date_from)
    if date_to:
        query = query.filter(Session.scheduled_start <= date_to)
    
    attendances = query.order_by(Session.scheduled_start.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student ID", "Student Name", "Username", "Module Code", "Module Name",
        "Session", "Scheduled Start", "Status", "Marked At"
    ])
    
    for a in attendances:
        writer.writerow([
            a.student.id,
            a.student.full_name,
            a.student.username,
            a.session.module.code,
            a.session.module.name,
            a.session.title,
            a.session.scheduled_start.isoformat(),
            a.status.value,
            a.marked_at.isoformat() if a.marked_at else "",
        ])
    
    output.seek(0)
    
    filename = f"attendance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Student Statistics (FR11)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/student-stats", response_model=StudentAttendanceStats)
def get_student_statistics(db: DBSession, current_user: CurrentUser):
    """Get detailed attendance statistics for the current student."""
    if current_user.role != Role.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can access their statistics")
    
    enrolled_modules = current_user.enrolled_modules
    
    module_stats = []
    total_sessions = 0
    total_present = 0
    total_late = 0
    total_absent = 0
    
    for module in enrolled_modules:
        # Get all ended sessions for this module
        sessions = db.query(Session).filter(
            Session.module_id == module.id,
            Session.status == SessionStatus.ENDED
        ).all()
        
        session_count = len(sessions)
        present = 0
        late = 0
        absent = 0
        
        for session in sessions:
            attendance = db.query(Attendance).filter(
                Attendance.session_id == session.id,
                Attendance.student_id == current_user.id
            ).first()
            
            if attendance:
                if attendance.status == AttendanceStatus.PRESENT:
                    present += 1
                elif attendance.status == AttendanceStatus.LATE:
                    late += 1
                else:
                    absent += 1
            else:
                absent += 1
        
        rate = ((present + late) / session_count * 100) if session_count > 0 else 0.0
        
        module_stats.append(ModuleAttendanceStats(
            module_id=module.id,
            module_code=module.code,
            module_name=module.name,
            total_sessions=session_count,
            attended_sessions=present + late,
            late_sessions=late,
            absent_sessions=absent,
            attendance_rate=round(rate, 2),
        ))
        
        total_sessions += session_count
        total_present += present
        total_late += late
        total_absent += absent
    
    overall_rate = ((total_present + total_late) / total_sessions * 100) if total_sessions > 0 else 0.0
    
    return StudentAttendanceStats(
        overall_rate=round(overall_rate, 2),
        total_sessions=total_sessions,
        present_count=total_present,
        late_count=total_late,
        absent_count=total_absent,
        modules=module_stats,
    )
