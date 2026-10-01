"""User & session-history database models"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import SQLModel, Field


class Role(str, Enum):
    teacher = "teacher"
    admin = "admin"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: Role = Field(default=Role.teacher)
    name: str
    school: Optional[str] = None
    grade_default: int = 10
    subject_default: str = "science"
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Syllabus(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "grade", "subject"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    grade: int
    subject: str
    content: str = ""
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class GoogleAccount(SQLModel, table=True):
    """A teacher's connected Google account, so Saathi can write notes into
    their own Drive as real Google Docs."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    google_email: str = ""
    refresh_token: str
    access_token: str = ""
    token_expiry: Optional[datetime] = None
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class NoteDoc(SQLModel, table=True):
    """One Google Doc of notes per class a teacher takes."""

    __table_args__ = (UniqueConstraint("user_id", "grade", "subject"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    grade: int
    subject: str
    doc_id: str
    doc_url: str
    title: str = ""
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TeacherTimetable(SQLModel, table=True):
    """The real weekly slots a grade/subject actually meets, read off the
    school's own timetable sheet — so generated schedules land on real class
    days instead of evenly-spread guesses."""

    __table_args__ = (UniqueConstraint("user_id", "grade", "subject"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    grade: int
    subject: str
    weekdays: str = ""  # comma-separated Python weekday numbers, Monday=0
    note: str = ""
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ScheduledClass(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    grade: int
    subject: str
    class_number: int
    chapter: str
    focus: str = ""
    scheduled_date: str  # ISO date (YYYY-MM-DD)
    calendar_event_id: str = ""  # set once synced to the teacher's Google Calendar
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SessionHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    intent: str
    topic: Optional[str] = None
    grade: int
    subject: str
    language: str
    content_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    rating: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
