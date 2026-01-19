"""Enrolment management endpoints (Admin only)."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.deps import DBSession, RequireAdmin
from app.models import Module, Role, User
from app.schemas import EnrolmentBulk, EnrolmentCreate

router = APIRouter(prefix="/enrolments", tags=["enrolments"])


@router.post("", status_code=status.HTTP_201_CREATED)
def enrol_student(payload: EnrolmentCreate, db: DBSession, _: RequireAdmin):
    """Enrol a student in a module."""
    student = db.query(User).filter(User.id == payload.student_id, User.role == Role.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    module = db.query(Module).filter(Module.id == payload.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    if student in module.enrolled_students:
        raise HTTPException(status_code=400, detail="Student already enrolled")
    module.enrolled_students.append(student)
    db.commit()
    return {"message": "Student enrolled successfully"}


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def enrol_students_bulk(payload: EnrolmentBulk, db: DBSession, _: RequireAdmin):
    """Enrol multiple students in a module."""
    module = db.query(Module).filter(Module.id == payload.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    enrolled_count = 0
    for student_id in payload.student_ids:
        student = db.query(User).filter(User.id == student_id, User.role == Role.STUDENT).first()
        if student and student not in module.enrolled_students:
            module.enrolled_students.append(student)
            enrolled_count += 1
    db.commit()
    return {"message": f"Enrolled {enrolled_count} students"}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def unenrol_student(student_id: int, module_id: int, db: DBSession, _: RequireAdmin):
    """Remove a student from a module."""
    student = db.query(User).filter(User.id == student_id).first()
    module = db.query(Module).filter(Module.id == module_id).first()
    if not student or not module:
        raise HTTPException(status_code=404, detail="Student or module not found")
    if student not in module.enrolled_students:
        raise HTTPException(status_code=400, detail="Student not enrolled in this module")
    module.enrolled_students.remove(student)
    db.commit()
