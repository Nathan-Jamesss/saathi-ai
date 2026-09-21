"""Auth routes: signup, login, profile"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from db import get_db
from auth.models import Role, SessionHistory, Syllabus, User
from auth.security import create_token, hash_password, verify_password
from auth.deps import get_current_user, require_admin

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


class HistoryEntry(BaseModel):
    id: int
    intent: str
    topic: Optional[str]
    grade: int
    subject: str
    language: str
    content_json: dict
    rating: int
    created_at: str


@router.get("/me/history", response_model=List[HistoryEntry])
def my_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.exec(
        select(SessionHistory)
        .where(SessionHistory.user_id == user.id)
        .order_by(SessionHistory.created_at.desc())
    ).all()
    return [
        HistoryEntry(
            id=r.id,
            intent=r.intent,
            topic=r.topic,
            grade=r.grade,
            subject=r.subject,
            language=r.language,
            content_json=r.content_json,
            rating=r.rating,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


class SyllabusResponse(BaseModel):
    grade: int
    subject: str
    content: str


class SyllabusSaveRequest(BaseModel):
    grade: int
    subject: str
    content: str


@router.get("/me/syllabus", response_model=SyllabusResponse)
def get_syllabus(
    grade: int,
    subject: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.exec(
        select(Syllabus).where(
            Syllabus.user_id == user.id,
            Syllabus.grade == grade,
            Syllabus.subject == subject,
        )
    ).first()
    return SyllabusResponse(grade=grade, subject=subject, content=row.content if row else "")


@router.put("/me/syllabus", response_model=SyllabusResponse)
def save_syllabus(
    req: SyllabusSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.exec(
        select(Syllabus).where(
            Syllabus.user_id == user.id,
            Syllabus.grade == req.grade,
            Syllabus.subject == req.subject,
        )
    ).first()
    if row:
        row.content = req.content
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = Syllabus(
            user_id=user.id, grade=req.grade, subject=req.subject, content=req.content
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return SyllabusResponse(grade=row.grade, subject=row.subject, content=row.content)


class TeacherCreateRequest(BaseModel):
    email: str
    password: str
    name: str
    school: Optional[str] = None


class TeacherResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    session_count: int


class TeacherPatchRequest(BaseModel):
    is_active: bool


def _teacher_response(db: Session, teacher: User) -> TeacherResponse:
    count = len(
        db.exec(
            select(SessionHistory).where(SessionHistory.user_id == teacher.id)
        ).all()
    )
    return TeacherResponse(
        id=teacher.id,
        email=teacher.email,
        name=teacher.name,
        is_active=teacher.is_active,
        session_count=count,
    )


@router.post("/admin/teachers", response_model=TeacherResponse)
def admin_create_teacher(
    req: TeacherCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.exec(select(User).where(User.email == req.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    teacher = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=Role.teacher,
        name=req.name,
        school=req.school,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _teacher_response(db, teacher)


@router.get("/admin/teachers", response_model=List[TeacherResponse])
def admin_list_teachers(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    teachers = db.exec(select(User).where(User.role == Role.teacher)).all()
    return [_teacher_response(db, t) for t in teachers]


@router.patch("/admin/teachers/{teacher_id}", response_model=TeacherResponse)
def admin_patch_teacher(
    teacher_id: int,
    req: TeacherPatchRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.get(User, teacher_id)
    if not teacher or teacher.role != Role.teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher.is_active = req.is_active
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _teacher_response(db, teacher)
