"""Auth routes: signup, login, profile"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from db import get_db
from auth.models import Role, User
from auth.security import create_token, hash_password, verify_password
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    school: Optional[str] = None
    grade_default: int = 10
    subject_default: str = "science"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    role: str
    name: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    school: Optional[str]
    grade_default: int
    subject_default: str


@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.exec(select(User).where(User.email == req.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=Role.teacher,
        name=req.name,
        school=req.school,
        grade_default=req.grade_default,
        subject_default=req.subject_default,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id, user.role.value)
    return TokenResponse(token=token, role=user.role.value, name=user.name)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.email == req.email)).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    token = create_token(user.id, user.role.value)
    return TokenResponse(token=token, role=user.role.value, name=user.name)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        school=user.school,
        grade_default=user.grade_default,
        subject_default=user.subject_default,
    )
