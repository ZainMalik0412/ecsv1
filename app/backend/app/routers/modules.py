"""Module management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DBSession, RequireAdmin, RequireLecturer
from app.models import Module, Role, User
from app.schemas import ModuleCreate, ModuleDetail, ModuleOut, ModuleUpdate, UserOut

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=List[ModuleOut])
def list_modules(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
):
    """List modules. Students see enrolled modules; lecturers see taught modules; admins see all."""
    query = db.query(Module)
    if current_user.role == Role.STUDENT:
        query = query.filter(Module.enrolled_students.any(User.id == current_user.id))
    elif current_user.role == Role.LECTURER:
        query = query.filter(Module.lecturer_id == current_user.id)
    modules = query.offset(skip).limit(limit).all()
    return [ModuleOut.model_validate(m) for m in modules]


@router.post("", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(payload: ModuleCreate, db: DBSession, _: RequireAdmin):
    """Create a new module (Admin only)."""
    if db.query(Module).filter(Module.code == payload.code).first():
        raise HTTPException(status_code=400, detail="Module code already exists")
    if payload.lecturer_id:
        lecturer = db.query(User).filter(User.id == payload.lecturer_id, User.role == Role.LECTURER).first()
        if not lecturer:
            raise HTTPException(status_code=400, detail="Lecturer not found")
    module = Module(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        lecturer_id=payload.lecturer_id,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return ModuleOut.model_validate(module)


@router.get("/{module_id}", response_model=ModuleDetail)
def get_module(module_id: int, db: DBSession, current_user: CurrentUser):
    """Get module details."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    # Authorization check
    if current_user.role == Role.STUDENT:
        if current_user not in module.enrolled_students:
            raise HTTPException(status_code=403, detail="Not enrolled in this module")
    elif current_user.role == Role.LECTURER:
        if module.lecturer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not assigned to this module")
    lecturer_out = None
    if module.lecturer:
        lecturer_out = UserOut(
            id=module.lecturer.id,
            username=module.lecturer.username,
            email=module.lecturer.email,
            full_name=module.lecturer.full_name,
            role=module.lecturer.role,
            is_active=module.lecturer.is_active,
            created_at=module.lecturer.created_at,
            has_face_registered=len(module.lecturer.face_encodings) > 0,
        )
    return ModuleDetail(
        id=module.id,
        code=module.code,
        name=module.name,
        description=module.description,
        lecturer_id=module.lecturer_id,
        created_at=module.created_at,
        lecturer=lecturer_out,
        enrolled_student_count=len(module.enrolled_students),
    )


@router.patch("/{module_id}", response_model=ModuleOut)
def update_module(module_id: int, payload: ModuleUpdate, db: DBSession, _: RequireAdmin):
    """Update a module (Admin only)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    if payload.code is not None:
        existing = db.query(Module).filter(Module.code == payload.code, Module.id != module_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Module code already exists")
        module.code = payload.code
    if payload.name is not None:
        module.name = payload.name
    if payload.description is not None:
        module.description = payload.description
    if payload.lecturer_id is not None:
        if payload.lecturer_id > 0:
            lecturer = db.query(User).filter(User.id == payload.lecturer_id, User.role == Role.LECTURER).first()
            if not lecturer:
                raise HTTPException(status_code=400, detail="Lecturer not found")
            module.lecturer_id = payload.lecturer_id
        else:
            module.lecturer_id = None
    db.commit()
    db.refresh(module)
    return ModuleOut.model_validate(module)


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(module_id: int, db: DBSession, _: RequireAdmin):
    """Delete a module (Admin only)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    db.delete(module)
    db.commit()


@router.get("/{module_id}/students", response_model=List[UserOut])
def list_module_students(module_id: int, db: DBSession, current_user: RequireLecturer):
    """List students enrolled in a module."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    if current_user.role == Role.LECTURER and module.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this module")
    return [
        UserOut(
            id=s.id,
            username=s.username,
            email=s.email,
            full_name=s.full_name,
            role=s.role,
            is_active=s.is_active,
            created_at=s.created_at,
            has_face_registered=len(s.face_encodings) > 0,
        )
        for s in module.enrolled_students
    ]
