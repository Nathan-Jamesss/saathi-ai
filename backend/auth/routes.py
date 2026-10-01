"""Auth routes: signup, login, profile"""
import csv
import io
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from db import get_db
from auth.models import (
    GoogleAccount,
    NoteDoc,
    Role,
    ScheduledClass,
    SessionHistory,
    Syllabus,
    TeacherTimetable,
    User,
)
from auth.security import create_token, hash_password, verify_password
from auth.deps import get_current_user, require_admin
from core.schedule import compute_class_dates, generate_schedule
from core.syllabus_pdf import extract_syllabus_from_pdf
from core.timetable_extract import extract_timetable
from core.google_calendar import delete_class_event, upsert_class_event
from core.google_docs import append_text, create_doc
from core.google_oauth import (
    build_authorize_url,
    exchange_code,
    expiry_from_now,
    fetch_google_email,
    is_configured,
    read_state,
    refresh_access_token,
)

logger = logging.getLogger(__name__)

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


@router.post("/me/syllabus/upload", response_model=SyllabusResponse)
async def upload_syllabus_pdf(
    grade: int = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pdf_bytes = await file.read()
    content = extract_syllabus_from_pdf(pdf_bytes)

    row = db.exec(
        select(Syllabus).where(
            Syllabus.user_id == user.id,
            Syllabus.grade == grade,
            Syllabus.subject == subject,
        )
    ).first()
    if row:
        row.content = content
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = Syllabus(user_id=user.id, grade=grade, subject=subject, content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return SyllabusResponse(grade=row.grade, subject=row.subject, content=row.content)


# ── Google account connection + notes as real Google Docs ──

class GoogleStatusResponse(BaseModel):
    configured: bool
    connected: bool
    google_email: str


class NotesDocResponse(BaseModel):
    grade: int
    subject: str
    doc_id: str
    doc_url: str


class NotesDocRequest(BaseModel):
    grade: int
    subject: str


class NotesAppendRequest(BaseModel):
    grade: int
    subject: str
    text: str


def _google_account(db: Session, user_id: int) -> Optional[GoogleAccount]:
    return db.exec(select(GoogleAccount).where(GoogleAccount.user_id == user_id)).first()


def _fresh_access_token(db: Session, account: GoogleAccount) -> str:
    """Google access tokens last about an hour; swap the long-lived refresh
    token for a new one whenever the current one is close to expiring."""
    expiry = account.token_expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    still_valid = (
        account.access_token
        and expiry is not None
        and expiry > datetime.now(timezone.utc) + timedelta(seconds=60)
    )
    if still_valid:
        return account.access_token

    tokens = refresh_access_token(account.refresh_token)
    account.access_token = tokens.get("access_token", "")
    account.token_expiry = expiry_from_now(tokens.get("expires_in"))
    db.add(account)
    db.commit()
    db.refresh(account)
    return account.access_token


@router.get("/me/google", response_model=GoogleStatusResponse)
def google_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _google_account(db, user.id)
    return GoogleStatusResponse(
        configured=is_configured(),
        connected=account is not None,
        google_email=account.google_email if account else "",
    )


@router.get("/google/authorize")
def google_authorize(user: User = Depends(get_current_user)):
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google notes are not set up yet — GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are missing",
        )
    return {"url": build_authorize_url(user.id)}


@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Google redirects the teacher's browser here after they approve."""
    frontend = os.environ.get("FRONTEND_URL", "https://frontend-vert-ten-18.vercel.app")
    try:
        user_id = read_state(state)
    except Exception:
        return RedirectResponse(f"{frontend}/dashboard.html?google=invalid_state")

    try:
        tokens = exchange_code(code)
    except Exception:
        return RedirectResponse(f"{frontend}/dashboard.html?google=failed")

    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    account = _google_account(db, user_id)

    if not account:
        if not refresh_token:
            return RedirectResponse(f"{frontend}/dashboard.html?google=no_refresh_token")
        account = GoogleAccount(user_id=user_id, refresh_token=refresh_token)

    # Google only re-sends a refresh token on first consent; keep the old one otherwise.
    if refresh_token:
        account.refresh_token = refresh_token
    account.access_token = access_token
    account.token_expiry = expiry_from_now(tokens.get("expires_in"))
    account.google_email = fetch_google_email(access_token)
    db.add(account)
    db.commit()

    return RedirectResponse(f"{frontend}/dashboard.html?google=connected")


@router.delete("/me/google")
def google_disconnect(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _google_account(db, user.id)
    if account:
        db.delete(account)
        db.commit()
    return {"ok": True}


def _note_doc(db: Session, user_id: int, grade: int, subject: str) -> Optional[NoteDoc]:
    return db.exec(
        select(NoteDoc).where(
            NoteDoc.user_id == user_id,
            NoteDoc.grade == grade,
            NoteDoc.subject == subject,
        )
    ).first()


@router.get("/me/notes", response_model=NotesDocResponse)
def get_notes_doc(grade: int, subject: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _note_doc(db, user.id, grade, subject)
    return NotesDocResponse(
        grade=grade,
        subject=subject,
        doc_id=row.doc_id if row else "",
        doc_url=row.doc_url if row else "",
    )


@router.post("/me/notes", response_model=NotesDocResponse)
def create_notes_doc(
    req: NotesDocRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = _note_doc(db, user.id, req.grade, req.subject)
    if existing:
        return NotesDocResponse(
            grade=existing.grade, subject=existing.subject,
            doc_id=existing.doc_id, doc_url=existing.doc_url,
        )

    account = _google_account(db, user.id)
    if not account:
        raise HTTPException(status_code=400, detail="Connect your Google account first")

    title = f"Saathi notes — Class {req.grade} {req.subject.title()}"
    created = create_doc(_fresh_access_token(db, account), title)

    row = NoteDoc(
        user_id=user.id,
        grade=req.grade,
        subject=req.subject,
        doc_id=created["doc_id"],
        doc_url=created["doc_url"],
        title=title,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return NotesDocResponse(
        grade=row.grade, subject=row.subject, doc_id=row.doc_id, doc_url=row.doc_url
    )


@router.post("/me/notes/append", response_model=NotesDocResponse)
def append_note(
    req: NotesAppendRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _note_doc(db, user.id, req.grade, req.subject)
    if not row:
        raise HTTPException(status_code=400, detail="Create a notes doc for this class first")

    account = _google_account(db, user.id)
    if not account:
        raise HTTPException(status_code=400, detail="Connect your Google account first")

    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    append_text(_fresh_access_token(db, account), row.doc_id, f"\n[{stamp}] {req.text}")

    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return NotesDocResponse(
        grade=row.grade, subject=row.subject, doc_id=row.doc_id, doc_url=row.doc_url
    )


class TimetableResponse(BaseModel):
    grade: int
    subject: str
    weekdays: List[int]
    note: str


def _timetable_weekdays(row: Optional[TeacherTimetable]) -> List[int]:
    if not row or not row.weekdays.strip():
        return []
    return [int(d) for d in row.weekdays.split(",") if d.strip()]


def _get_timetable_row(db: Session, user_id: int, grade: int, subject: str) -> Optional[TeacherTimetable]:
    return db.exec(
        select(TeacherTimetable).where(
            TeacherTimetable.user_id == user_id,
            TeacherTimetable.grade == grade,
            TeacherTimetable.subject == subject,
        )
    ).first()


@router.get("/me/timetable", response_model=TimetableResponse)
def get_timetable(grade: int, subject: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _get_timetable_row(db, user.id, grade, subject)
    return TimetableResponse(
        grade=grade,
        subject=subject,
        weekdays=_timetable_weekdays(row),
        note=row.note if row else "",
    )


@router.post("/me/timetable/upload", response_model=TimetableResponse)
async def upload_timetable(
    grade: int = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    extracted = extract_timetable(
        file_bytes, file.content_type or "application/pdf", grade, subject
    )

    row = _get_timetable_row(db, user.id, grade, subject)
    if not row:
        row = TeacherTimetable(user_id=user.id, grade=grade, subject=subject)
    row.weekdays = ",".join(str(d) for d in extracted["weekdays"])
    row.note = extracted["note"]
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)

    return TimetableResponse(
        grade=row.grade,
        subject=row.subject,
        weekdays=_timetable_weekdays(row),
        note=row.note,
    )


class ScheduleGenerateRequest(BaseModel):
    grade: int
    subject: str
    start_date: date
    end_date: date
    classes_per_week: int


class ScheduledClassResponse(BaseModel):
    id: int
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
async def generate_class_schedule(
    req: ScheduleGenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    syllabus = db.exec(
        select(Syllabus).where(
            Syllabus.user_id == user.id,
            Syllabus.grade == req.grade,
            Syllabus.subject == req.subject,
        )
    ).first()
    if not syllabus or not syllabus.content.strip():
        raise HTTPException(status_code=400, detail="Save a syllabus for this grade/subject first")

    # The school's own timetable, if uploaded, decides which days classes land on.
    real_weekdays = _timetable_weekdays(_get_timetable_row(db, user.id, req.grade, req.subject))

    class_dates = compute_class_dates(
        req.start_date, req.end_date, req.classes_per_week, weekdays=real_weekdays
    )
    if not class_dates:
        raise HTTPException(status_code=400, detail="No class dates fall in that range")

    sessions = await generate_schedule(syllabus.content, req.grade, req.subject, class_dates)

    existing = db.exec(
        select(ScheduledClass).where(
            ScheduledClass.user_id == user.id,
            ScheduledClass.grade == req.grade,
            ScheduledClass.subject == req.subject,
        )
    ).all()
    for row in existing:
        db.delete(row)
    db.commit()

    created = []
    for i, (session, class_date) in enumerate(zip(sessions, class_dates), start=1):
        row = ScheduledClass(
            user_id=user.id,
            grade=req.grade,
            subject=req.subject,
            class_number=i,
            chapter=session.get("chapter", ""),
            focus=session.get("focus", ""),
            scheduled_date=class_date.isoformat(),
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)

    return [_schedule_response(r) for r in created]


class CalendarSyncRequest(BaseModel):
    grade: int
    subject: str


class CalendarSyncResponse(BaseModel):
    synced: int


@router.post("/me/schedule/sync-calendar", response_model=CalendarSyncResponse)
def sync_schedule_to_calendar(
    req: CalendarSyncRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Put this class's whole schedule on the teacher's own Google Calendar.
    Re-syncing updates the same events instead of making duplicates."""
    account = _google_account(db, user.id)
    if not account:
        raise HTTPException(status_code=400, detail="Connect your Google account first")

    rows = db.exec(
        select(ScheduledClass)
        .where(
            ScheduledClass.user_id == user.id,
            ScheduledClass.grade == req.grade,
            ScheduledClass.subject == req.subject,
        )
        .order_by(ScheduledClass.scheduled_date)
    ).all()
    if not rows:
        raise HTTPException(status_code=400, detail="Generate a timetable for this class first")

    access_token = _fresh_access_token(db, account)
    synced = 0
    for row in rows:
        summary = f"Class {row.grade} {row.subject.title()} — {row.chapter}"
        event_id = upsert_class_event(
            access_token,
            row.calendar_event_id,
            summary,
            row.focus,
            row.scheduled_date,
        )
        if event_id != row.calendar_event_id:
            row.calendar_event_id = event_id
            db.add(row)
        synced += 1
    db.commit()

    return CalendarSyncResponse(synced=synced)


@router.get("/me/schedule", response_model=List[ScheduledClassResponse])
def list_schedule(
    grade: int,
    subject: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.exec(
        select(ScheduledClass)
        .where(
            ScheduledClass.user_id == user.id,
            ScheduledClass.grade == grade,
            ScheduledClass.subject == subject,
        )
        .order_by(ScheduledClass.scheduled_date)
    ).all()
    return [_schedule_response(r) for r in rows]


def _remove_calendar_event(db: Session, row: ScheduledClass) -> None:
    """Best-effort: drop the matching Google Calendar event so a deleted class
    doesn't linger on the teacher's calendar. Never blocks the delete itself."""
    if not row.calendar_event_id:
        return
    account = _google_account(db, row.user_id)
    if not account:
        return
    try:
        delete_class_event(_fresh_access_token(db, account), row.calendar_event_id)
    except Exception:
        logger.warning("Could not remove calendar event for class %s", row.id, exc_info=True)


@router.delete("/me/schedule/{entry_id}")
def delete_scheduled_class(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(ScheduledClass, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    _remove_calendar_event(db, row)
    db.delete(row)
    db.commit()
    return {"ok": True}


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
    last_active: Optional[str]


class TeacherPatchRequest(BaseModel):
    is_active: bool


def _teacher_response(db: Session, teacher: User) -> TeacherResponse:
    sessions = db.exec(
        select(SessionHistory).where(SessionHistory.user_id == teacher.id)
    ).all()
    last_active = max((s.created_at for s in sessions), default=None)
    return TeacherResponse(
        id=teacher.id,
        email=teacher.email,
        name=teacher.name,
        is_active=teacher.is_active,
        session_count=len(sessions),
        last_active=last_active.isoformat() if last_active else None,
    )


GRADES = [8, 9, 10, 11, 12]
SUBJECTS = ["science", "mathematics", "history", "geography", "political science", "economics", "english"]


class CoverageCell(BaseModel):
    grade: int
    subject: str
    teachers: List[str]


class AdminOverviewResponse(BaseModel):
    total_teachers: int
    active_teachers: int
    total_sessions: int
    total_scheduled_classes: int
    coverage: List[CoverageCell]


class TeacherProgressRow(BaseModel):
    teacher_id: int
    teacher_name: str
    email: str
    is_active: bool
    total_classes: int
    done_classes: int
    percent_done: int
    classes_this_week: int
    last_active: Optional[str]


def _teacher_progress_rows(db: Session) -> List[TeacherProgressRow]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    classes = db.exec(select(ScheduledClass)).all()
    sessions = db.exec(select(SessionHistory)).all()

    by_teacher: dict = {}
    for c in classes:
        stats = by_teacher.setdefault(c.user_id, {"total": 0, "done": 0, "week": 0})
        stats["total"] += 1
        if c.scheduled_date < today.isoformat():
            stats["done"] += 1
        if week_start.isoformat() <= c.scheduled_date <= week_end.isoformat():
            stats["week"] += 1

    last_seen: dict = {}
    for s in sessions:
        if s.user_id not in last_seen or s.created_at > last_seen[s.user_id]:
            last_seen[s.user_id] = s.created_at

    rows = []
    for t in db.exec(select(User).where(User.role == Role.teacher)).all():
        stats = by_teacher.get(t.id, {"total": 0, "done": 0, "week": 0})
        total = stats["total"]
        seen = last_seen.get(t.id)
        rows.append(
            TeacherProgressRow(
                teacher_id=t.id,
                teacher_name=t.name,
                email=t.email,
                is_active=t.is_active,
                total_classes=total,
                done_classes=stats["done"],
                percent_done=round(stats["done"] / total * 100) if total else 0,
                classes_this_week=stats["week"],
                last_active=seen.isoformat() if seen else None,
            )
        )
    return rows


@router.get("/admin/progress", response_model=List[TeacherProgressRow])
def admin_progress(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Per-teacher syllabus progress and workload — shows who is falling behind
    and who is carrying the most classes this week."""
    return _teacher_progress_rows(db)


class ActivityDay(BaseModel):
    date: str
    sessions: int


@router.get("/admin/activity", response_model=List[ActivityDay])
def admin_activity(
    days: int = 14,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """AI lessons generated per day, oldest first, ending today."""
    days = max(1, min(days, 90))
    today = date.today()
    counts = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days)}

    for s in db.exec(select(SessionHistory)).all():
        key = s.created_at.date().isoformat()
        if key in counts:
            counts[key] += 1

    return [ActivityDay(date=d, sessions=counts[d]) for d in sorted(counts)]


class PasswordResetRequest(BaseModel):
    password: str


@router.patch("/admin/teachers/{teacher_id}/password")
def admin_reset_teacher_password(
    teacher_id: int,
    req: PasswordResetRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """There is no email reset flow, so a locked-out teacher needs an admin to
    set a new password for them."""
    teacher = db.get(User, teacher_id)
    if not teacher or teacher.role != Role.teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    teacher.password_hash = hash_password(req.password)
    db.add(teacher)
    db.commit()
    return {"ok": True}


@router.get("/admin/report.csv")
def admin_report_csv(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """One row per teacher, ready to hand to a principal or education officer."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Teacher", "Email", "Status", "Total classes", "Classes done",
        "Percent done", "Classes this week", "Last active",
    ])
    for r in _teacher_progress_rows(db):
        writer.writerow([
            r.teacher_name,
            r.email,
            "active" if r.is_active else "deactivated",
            r.total_classes,
            r.done_classes,
            f"{r.percent_done}%",
            r.classes_this_week,
            r.last_active[:10] if r.last_active else "never",
        ])

    filename = f"saathi-report-{date.today().isoformat()}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class AdminScheduleRow(BaseModel):
    id: int
    teacher_id: int
    teacher_name: str
    grade: int
    subject: str
    class_number: int
    chapter: str
    focus: str
    scheduled_date: str


class AdminScheduleCreateRequest(BaseModel):
    teacher_id: int
    grade: int
    subject: str
    chapter: str
    focus: str = ""
    scheduled_date: date


class AdminSchedulePatchRequest(BaseModel):
    chapter: Optional[str] = None
    focus: Optional[str] = None
    scheduled_date: Optional[date] = None


def _admin_schedule_row(row: ScheduledClass, teacher: User) -> AdminScheduleRow:
    return AdminScheduleRow(
        id=row.id,
        teacher_id=teacher.id,
        teacher_name=teacher.name,
        grade=row.grade,
        subject=row.subject,
        class_number=row.class_number,
        chapter=row.chapter,
        focus=row.focus,
        scheduled_date=row.scheduled_date,
    )


@router.get("/admin/schedule", response_model=List[AdminScheduleRow])
def admin_list_schedule(
    days: int = 7,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Every teacher's upcoming classes, so an admin can see who is teaching
    what over the next few days and adjust it."""
    today = date.today()
    until = today + timedelta(days=days)
    rows = db.exec(
        select(ScheduledClass)
        .where(
            ScheduledClass.scheduled_date >= today.isoformat(),
            ScheduledClass.scheduled_date <= until.isoformat(),
        )
        .order_by(ScheduledClass.scheduled_date)
    ).all()

    teachers = {t.id: t for t in db.exec(select(User)).all()}
    return [_admin_schedule_row(r, teachers[r.user_id]) for r in rows if r.user_id in teachers]


@router.post("/admin/schedule", response_model=AdminScheduleRow)
def admin_create_scheduled_class(
    req: AdminScheduleCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.get(User, req.teacher_id)
    if not teacher or teacher.role != Role.teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    existing = db.exec(
        select(ScheduledClass).where(
            ScheduledClass.user_id == teacher.id,
            ScheduledClass.grade == req.grade,
            ScheduledClass.subject == req.subject,
        )
    ).all()

    row = ScheduledClass(
        user_id=teacher.id,
        grade=req.grade,
        subject=req.subject,
        class_number=len(existing) + 1,
        chapter=req.chapter,
        focus=req.focus,
        scheduled_date=req.scheduled_date.isoformat(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _admin_schedule_row(row, teacher)


@router.patch("/admin/schedule/{entry_id}", response_model=AdminScheduleRow)
def admin_patch_scheduled_class(
    entry_id: int,
    req: AdminSchedulePatchRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(ScheduledClass, entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")

    if req.chapter is not None:
        row.chapter = req.chapter
    if req.focus is not None:
        row.focus = req.focus
    if req.scheduled_date is not None:
        row.scheduled_date = req.scheduled_date.isoformat()

    db.add(row)
    db.commit()
    db.refresh(row)
    return _admin_schedule_row(row, db.get(User, row.user_id))


@router.delete("/admin/schedule/{entry_id}")
def admin_delete_scheduled_class(
    entry_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(ScheduledClass, entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    _remove_calendar_event(db, row)
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/admin/overview", response_model=AdminOverviewResponse)
def admin_overview(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    teachers = db.exec(select(User).where(User.role == Role.teacher)).all()
    user_by_id = {t.id: t for t in teachers}

    syllabus_rows = db.exec(select(Syllabus)).all()
    coverage_map: dict = {}
    for row in syllabus_rows:
        teacher = user_by_id.get(row.user_id)
        if not teacher:
            continue
        key = (row.grade, row.subject)
        names = coverage_map.setdefault(key, [])
        if teacher.name not in names:
            names.append(teacher.name)

    coverage = [
        CoverageCell(grade=grade, subject=subject, teachers=coverage_map.get((grade, subject), []))
        for grade in GRADES
        for subject in SUBJECTS
    ]

    return AdminOverviewResponse(
        total_teachers=len(teachers),
        active_teachers=sum(1 for t in teachers if t.is_active),
        total_sessions=len(db.exec(select(SessionHistory)).all()),
        total_scheduled_classes=len(db.exec(select(ScheduledClass)).all()),
        coverage=coverage,
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
