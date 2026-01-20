"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import create_access_token, hash_password, verify_password
from app.deps import CurrentUser, DBSession
from app.models import Role, User
from app.schemas import LoginRequest, Token, UserMe, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: DBSession = None):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    access_token = create_access_token(subject=user.username, role=user.role)
    return Token(access_token=access_token)


@router.post("/login/json", response_model=Token)
def login_json(payload: LoginRequest, db: DBSession):
    """Authenticate user via JSON body and return JWT token."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    access_token = create_access_token(subject=user.username, role=user.role)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserMe)
def get_current_user_info(current_user: CurrentUser):
    """Get current authenticated user's information."""
    return UserMe(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        has_face_registered=len(current_user.face_encodings) > 0,
        enrolled_module_ids=[m.id for m in current_user.enrolled_modules],
        taught_module_ids=[m.id for m in current_user.taught_modules],
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: DBSession):
    """
    Register a new user account.
    
    New users are created as students by default.
    After signing up, users should register their face for attendance verification.
    """
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=Role.STUDENT,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        has_face_registered=False,
    )
