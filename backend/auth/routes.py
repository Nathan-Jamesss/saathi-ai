"""Auth routes: signup, login, profile — Firestore-backed"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from auth import firestore_repo
from auth.models import Role, ScheduledClass, User
from auth.security import create_token, hash_password, verify_password
from auth.deps import get_current_user, require_admin
from core.schedule import compute_class_dates, generate_schedule
from core.syllabus_pdf import extract_syllabus_from_pdf

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
    id: str
    email: str
    name: str
    role: str
    school: Optional[str]
    grade_default: int
    subject_default: str


@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest):
    if firestore_repo.get_user_by_email(req.email):
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
    user = firestore_repo.create_user(user)
    token = create_token(user.id, user.role.value)
    return TokenResponse(token=token, role=user.role.value, name=user.name)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = firestore_repo.get_user_by_email(req.email)
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
    id: str
    intent: str
    topic: Optional[str]
    grade: int
    subject: str
    language: str
    content_json: dict
    rating: int
    created_at: str


@router.get("/me/history", response_model=List[HistoryEntry])
def my_history(user: User = Depends(get_current_user)):
    rows = firestore_repo.list_history(user.id)
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
def get_syllabus(grade: int, subject: str, user: User = Depends(get_current_user)):
    row = firestore_repo.get_syllabus(user.id, grade, subject)
    return SyllabusResponse(grade=grade, subject=subject, content=row.content if row else "")


@router.put("/me/syllabus", response_model=SyllabusResponse)
def save_syllabus(req: SyllabusSaveRequest, user: User = Depends(get_current_user)):
    row = firestore_repo.save_syllabus(user.id, req.grade, req.subject, req.content)
    return SyllabusResponse(grade=row.grade, subject=row.subject, content=row.content)


@router.post("/me/syllabus/upload", response_model=SyllabusResponse)
async def upload_syllabus_pdf(
    grade: int = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    pdf_bytes = await file.read()
    content = extract_syllabus_from_pdf(pdf_bytes)
    row = firestore_repo.save_syllabus(user.id, grade, subject, content)
    return SyllabusResponse(grade=row.grade, subject=row.subject, content=row.content)


class ScheduleGenerateRequest(BaseModel):
    grade: int
    subject: str
    start_date: date
    end_date: date
    classes_per_week: int


class ScheduledClassResponse(BaseModel):
    id: str
    class_number: int
    chapter: str
    focus: str
    scheduled_date: str


def _schedule_response(row: ScheduledClass) -> ScheduledClassResponse:
    return ScheduledClassResponse(
        id=row.id,
        class_number=row.class_number,
        chapter=row.chapter,
        focus=row.focus,
        scheduled_date=row.scheduled_date,
    )


@router.post("/me/schedule/generate", response_model=List[ScheduledClassResponse])
async def generate_class_schedule(req: ScheduleGenerateRequest, user: User = Depends(get_current_user)):
    syllabus = firestore_repo.get_syllabus(user.id, req.grade, req.subject)
    if not syllabus or not syllabus.content.strip():
        raise HTTPException(status_code=400, detail="Save a syllabus for this grade/subject first")

    class_dates = compute_class_dates(req.start_date, req.end_date, req.classes_per_week)
    if not class_dates:
        raise HTTPException(status_code=400, detail="No class dates fall in that range")

    sessions = await generate_schedule(syllabus.content, req.grade, req.subject, class_dates)

    firestore_repo.delete_schedule_for(user.id, req.grade, req.subject)

    to_create = [
        ScheduledClass(
            user_id=user.id,
            grade=req.grade,
            subject=req.subject,
            class_number=i,
            chapter=session.get("chapter", ""),
            focus=session.get("focus", ""),
            scheduled_date=class_date.isoformat(),
        )
        for i, (session, class_date) in enumerate(zip(sessions, class_dates), start=1)
    ]
    created = firestore_repo.create_scheduled_classes(to_create)
    return [_schedule_response(r) for r in created]


@router.get("/me/schedule", response_model=List[ScheduledClassResponse])
def list_schedule(grade: int, subject: str, user: User = Depends(get_current_user)):
    rows = firestore_repo.list_schedule(user.id, grade, subject)
    return [_schedule_response(r) for r in rows]


@router.delete("/me/schedule/{entry_id}")
def delete_scheduled_class(entry_id: str, user: User = Depends(get_current_user)):
    row = firestore_repo.get_scheduled_class(entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    firestore_repo.delete_scheduled_class(entry_id)
    return {"ok": True}


class TeacherCreateRequest(BaseModel):
    email: str
    password: str
    name: str
    school: Optional[str] = None


class TeacherResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    session_count: int


class TeacherPatchRequest(BaseModel):
    is_active: bool


def _teacher_response(teacher: User) -> TeacherResponse:
    return TeacherResponse(
        id=teacher.id,
        email=teacher.email,
        name=teacher.name,
        is_active=teacher.is_active,
        session_count=firestore_repo.count_sessions_for_user(teacher.id),
    )


@router.post("/admin/teachers", response_model=TeacherResponse)
def admin_create_teacher(req: TeacherCreateRequest, _admin: User = Depends(require_admin)):
    if firestore_repo.get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    teacher = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=Role.teacher,
        name=req.name,
        school=req.school,
    )
    teacher = firestore_repo.create_user(teacher)
    return _teacher_response(teacher)


@router.get("/admin/teachers", response_model=List[TeacherResponse])
def admin_list_teachers(_admin: User = Depends(require_admin)):
    return [_teacher_response(t) for t in firestore_repo.list_teachers()]


@router.patch("/admin/teachers/{teacher_id}", response_model=TeacherResponse)
def admin_patch_teacher(teacher_id: str, req: TeacherPatchRequest, _admin: User = Depends(require_admin)):
    teacher = firestore_repo.get_user(teacher_id)
    if not teacher or teacher.role != Role.teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    firestore_repo.update_user_fields(teacher_id, {"is_active": req.is_active})
    teacher.is_active = req.is_active
    return _teacher_response(teacher)
