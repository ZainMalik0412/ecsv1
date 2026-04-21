# Pydantic schemas for request/response validation.

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AttendanceStatus, Role, SessionStatus


def _to_naive_utc(v):
    # Normalise incoming datetimes to timezone-naive UTC so they can be compared
    # against datetime.utcnow() and stored consistently in the DB. The frontend
    # sends ISO strings like '2026-04-21T23:05:55.061716Z' which Pydantic parses
    # as tz-aware; the rest of the backend is tz-naive.
    if isinstance(v, datetime) and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    role: Role
    exp: int


class LoginRequest(BaseModel):
    username: str
    password: str


# User
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[str] = None
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Role = Role.STUDENT


class UserCreate(UserBase):
    password: str = Field(..., min_length=4)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=4)
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    has_face_registered: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserMe(UserOut):
    enrolled_module_ids: List[int] = []
    taught_module_ids: List[int] = []


# Module
class ModuleBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ModuleCreate(ModuleBase):
    lecturer_id: Optional[int] = None


class ModuleUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    lecturer_id: Optional[int] = None


class ModuleOut(ModuleBase):
    id: int
    lecturer_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModuleDetail(ModuleOut):
    lecturer: Optional[UserOut] = None
    enrolled_student_count: int = 0


# Enrolment
class EnrolmentCreate(BaseModel):
    student_id: int
    module_id: int


class EnrolmentBulk(BaseModel):
    student_ids: List[int]
    module_id: int


# Session
class SessionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    scheduled_start: datetime
    scheduled_end: datetime
    late_threshold_minutes: int = 15

    @field_validator("scheduled_start", "scheduled_end")
    @classmethod
    def _strip_tz(cls, v):
        return _to_naive_utc(v)


class SessionCreate(SessionBase):
    module_id: int


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    late_threshold_minutes: Optional[int] = None

    @field_validator("scheduled_start", "scheduled_end")
    @classmethod
    def _strip_tz(cls, v):
        return _to_naive_utc(v)


class SessionOut(SessionBase):
    id: int
    module_id: int
    status: SessionStatus
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDetail(SessionOut):
    module: Optional[ModuleOut] = None
    attendance_count: int = 0
    present_count: int = 0


# Attendance
class AttendanceBase(BaseModel):
    status: AttendanceStatus = AttendanceStatus.ABSENT
    notes: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    session_id: int
    student_id: int


class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = None


class AttendanceOut(AttendanceBase):
    id: int
    session_id: int
    student_id: int
    marked_at: Optional[datetime]
    face_confidence: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class AttendanceDetail(AttendanceOut):
    student: Optional[UserOut] = None


# Face Registration
class FaceRegisterRequest(BaseModel):
    image_base64: str


class FaceRegisterResponse(BaseModel):
    success: bool
    message: str
    encodings_count: int = 0


class FaceVerifyRequest(BaseModel):
    session_id: int
    image_base64: str


class FaceVerifyResponse(BaseModel):
    success: bool
    matched: bool
    confidence: Optional[float] = None
    attendance_id: Optional[int] = None
    message: str


# Bulk face enrolment (admin only)
class BulkFaceEnrollRequest(BaseModel):
    user_id: int
    images_base64: List[str] = Field(..., min_length=1, max_length=50)
    replace_existing: bool = False


class BulkFaceEnrollImageResult(BaseModel):
    index: int
    success: bool
    message: str
    filename: Optional[str] = None


class BulkFaceEnrollResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    enrolled: int
    failed: int
    total_encodings: int
    results: List[BulkFaceEnrollImageResult]


# Dashboard / Reports
class DashboardStats(BaseModel):
    total_students: int
    total_lecturers: int
    total_modules: int
    total_sessions: int
    active_sessions: int
    attendance_rate: float


class AttendanceReportRow(BaseModel):
    student_id: int
    student_name: str
    student_username: str
    session_id: int
    session_title: str
    module_code: str
    module_name: str
    scheduled_start: datetime
    status: AttendanceStatus
    marked_at: Optional[datetime]


# Live Recognition (FR6-FR8)
class LiveRecognitionRequest(BaseModel):
    image_base64: str


class FaceBox(BaseModel):
    # Bounding box coordinates for a detected face.
    top: int
    right: int
    bottom: int
    left: int


class RecognizedStudent(BaseModel):
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    username: Optional[str] = None
    confidence: float
    status: Optional[str] = None
    already_marked: bool = False
    face_box: Optional[FaceBox] = None
    is_unknown: bool = False


class LiveRecognitionResponse(BaseModel):
    success: bool
    message: str
    recognized_students: List[RecognizedStudent] = []
    frame_processed: bool = False


class LiveSessionState(BaseModel):
    session_id: int
    status: SessionStatus
    title: str
    module_code: str
    module_name: str
    actual_start: Optional[datetime]
    total_enrolled: int
    present_count: int
    late_count: int
    absent_count: int


class LiveAttendanceStudent(BaseModel):
    student_id: int
    student_name: str
    username: str
    status: AttendanceStatus
    marked_at: Optional[datetime]
    face_confidence: Optional[float]
    has_face_registered: bool


class LiveAttendanceList(BaseModel):
    session_id: int
    students: List[LiveAttendanceStudent]


# Student Statistics (FR11)
class ModuleAttendanceStats(BaseModel):
    module_id: int
    module_code: str
    module_name: str
    total_sessions: int
    attended_sessions: int
    late_sessions: int
    absent_sessions: int
    attendance_rate: float


class StudentAttendanceStats(BaseModel):
    overall_rate: float
    total_sessions: int
    present_count: int
    late_count: int
    absent_count: int
    modules: List[ModuleAttendanceStats]
