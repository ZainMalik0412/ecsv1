# Face registration and verification endpoints.

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DBSession, RequireAdmin
from app.models import Attendance, AttendanceStatus, FaceEncoding, Role, Session, SessionStatus, User
from app.schemas import (
    BulkFaceEnrollImageResult,
    BulkFaceEnrollRequest,
    BulkFaceEnrollResponse,
    FaceRegisterRequest,
    FaceRegisterResponse,
    FaceVerifyRequest,
    FaceVerifyResponse,
)
from app.services.face_recognition import (
    bytes_to_encoding,
    compare_faces,
    encoding_to_bytes,
    extract_and_encode_face,
)

router = APIRouter(prefix="/face", tags=["face"])


@router.post("/register", response_model=FaceRegisterResponse)
def register_face(payload: FaceRegisterRequest, db: DBSession, current_user: CurrentUser):
    # Register a face encoding for the current user.
    # Students register their own face. Admins can register faces for any user
    # by passing user_id in the request (not implemented here for simplicity).
    if current_user.role not in [Role.STUDENT, Role.ADMIN]:
        raise HTTPException(status_code=403, detail="Only students can register faces")
    
    try:
        encoding, message = extract_and_encode_face(payload.image_base64)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Face detection failed: {str(e)}")
    
    if encoding is None:
        return FaceRegisterResponse(success=False, message=message, encodings_count=0)
    
    # Store the encoding
    face_encoding = FaceEncoding(
        user_id=current_user.id,
        encoding=encoding_to_bytes(encoding),
    )
    db.add(face_encoding)
    db.commit()
    
    # Count total encodings for this user
    count = db.query(FaceEncoding).filter(FaceEncoding.user_id == current_user.id).count()
    
    return FaceRegisterResponse(
        success=True,
        message="Face registered successfully",
        encodings_count=count,
    )


@router.delete("/register", response_model=FaceRegisterResponse)
def clear_face_registrations(db: DBSession, current_user: CurrentUser):
    # Clear all face registrations for the current user.
    if current_user.role not in [Role.STUDENT, Role.ADMIN]:
        raise HTTPException(status_code=403, detail="Only students can manage their face registrations")
    
    deleted = db.query(FaceEncoding).filter(FaceEncoding.user_id == current_user.id).delete()
    db.commit()
    
    return FaceRegisterResponse(
        success=True,
        message=f"Cleared {deleted} face registration(s)",
        encodings_count=0,
    )


@router.post("/verify", response_model=FaceVerifyResponse)
def verify_face_and_mark_attendance(
    payload: FaceVerifyRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    # Verify face and mark attendance for a session.
    #
    # This endpoint:
    # 1. Checks the session is active
    # 2. Checks the student is enrolled in the module
    # 3. Extracts face encoding from the submitted image
    # 4. Compares against the student's registered face encodings
    # 5. If matched, marks attendance (PRESENT or LATE based on threshold)
    if current_user.role != Role.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can mark attendance via face verification")
    
    # Get session
    session = db.query(Session).filter(Session.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.ACTIVE:
        return FaceVerifyResponse(
            success=False,
            matched=False,
            message=f"Session is not active (status: {session.status.value})",
        )
    
    # Check enrollment
    enrolled_module_ids = [m.id for m in current_user.enrolled_modules]
    if session.module_id not in enrolled_module_ids:
        raise HTTPException(status_code=403, detail="Not enrolled in this module")
    
    # Check if already marked present
    existing = db.query(Attendance).filter(
        Attendance.session_id == payload.session_id,
        Attendance.student_id == current_user.id,
    ).first()
    
    if existing and existing.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
        return FaceVerifyResponse(
            success=True,
            matched=True,
            confidence=existing.face_confidence,
            attendance_id=existing.id,
            message="Attendance already marked",
        )
    
    # Get user's face encodings
    face_encodings = db.query(FaceEncoding).filter(FaceEncoding.user_id == current_user.id).all()
    if not face_encodings:
        return FaceVerifyResponse(
            success=False,
            matched=False,
            message="No face registered. Please register your face first.",
        )
    
    # Extract face from submitted image
    try:
        submitted_encoding, message = extract_and_encode_face(payload.image_base64)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        return FaceVerifyResponse(
            success=False,
            matched=False,
            message=f"Face detection failed: {str(e)}",
        )
    
    if submitted_encoding is None:
        return FaceVerifyResponse(success=False, matched=False, message=message)
    
    # Compare faces
    known_encodings = [bytes_to_encoding(fe.encoding) for fe in face_encodings]
    matched, confidence = compare_faces(known_encodings, submitted_encoding)
    
    if not matched:
        return FaceVerifyResponse(
            success=True,
            matched=False,
            confidence=confidence,
            message="Face did not match registered face",
        )
    
    # Determine if late
    now = datetime.utcnow()
    late_threshold = session.actual_start + timedelta(minutes=session.late_threshold_minutes)
    status = AttendanceStatus.LATE if now > late_threshold else AttendanceStatus.PRESENT
    
    # Update or create attendance record
    if existing:
        existing.status = status
        existing.marked_at = now
        existing.face_confidence = confidence
        attendance_id = existing.id
    else:
        attendance = Attendance(
            session_id=payload.session_id,
            student_id=current_user.id,
            status=status,
            marked_at=now,
            face_confidence=confidence,
        )
        db.add(attendance)
        db.flush()
        attendance_id = attendance.id
    
    db.commit()
    
    return FaceVerifyResponse(
        success=True,
        matched=True,
        confidence=confidence,
        attendance_id=attendance_id,
        message=f"Attendance marked as {status.value}",
    )


# Admin-only bulk face enrolment
@router.post("/admin/bulk-enroll", response_model=BulkFaceEnrollResponse)
def admin_bulk_enroll_faces(
    payload: BulkFaceEnrollRequest,
    db: DBSession,
    _: RequireAdmin,
):
    # Bulk-enroll face encodings for a given user (admin only).
    #
    # For each submitted image the endpoint runs the existing single-face
    # extraction pipeline. Successful embeddings are stored against the target
    # user. If `replace_existing` is true, all prior encodings for that user are
    # deleted before the new ones are saved. Results are reported per image so
    # the caller can see which images succeeded and which failed.
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.replace_existing:
        db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).delete()
        db.flush()

    results = []
    enrolled = 0
    failed = 0

    for idx, image_b64 in enumerate(payload.images_base64):
        try:
            encoding, message = extract_and_encode_face(image_b64)
        except Exception as e:
            failed += 1
            results.append(BulkFaceEnrollImageResult(
                index=idx,
                success=False,
                message=f"Processing error: {str(e)}",
            ))
            continue

        if encoding is None:
            failed += 1
            results.append(BulkFaceEnrollImageResult(
                index=idx,
                success=False,
                message=message,
            ))
            continue

        face_encoding = FaceEncoding(
            user_id=user.id,
            encoding=encoding_to_bytes(encoding),
        )
        db.add(face_encoding)
        enrolled += 1
        results.append(BulkFaceEnrollImageResult(
            index=idx,
            success=True,
            message="Enrolled",
        ))

    db.commit()

    total = db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).count()

    return BulkFaceEnrollResponse(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        enrolled=enrolled,
        failed=failed,
        total_encodings=total,
        results=results,
    )


@router.delete("/admin/clear/{user_id}", response_model=FaceRegisterResponse)
def admin_clear_user_faces(user_id: int, db: DBSession, _: RequireAdmin):
    # Clear all face encodings for a specific user (admin only).
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    deleted = db.query(FaceEncoding).filter(FaceEncoding.user_id == user_id).delete()
    db.commit()

    return FaceRegisterResponse(
        success=True,
        message=f"Cleared {deleted} face registration(s) for {user.username}",
        encodings_count=0,
    )
