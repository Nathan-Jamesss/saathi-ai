"""User & session-history data models — plain Pydantic (Firestore is schemaless,
these exist for validation/typing, not ORM table definitions)."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    teacher = "teacher"
    admin = "admin"


class User(BaseModel):
    id: Optional[str] = None
    email: str
    password_hash: str
    role: Role = Role.teacher
    name: str
    school: Optional[str] = None
    grade_default: int = 10
    subject_default: str = "science"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Syllabus(BaseModel):
    user_id: str
    grade: int
    subject: str
    content: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionHistory(BaseModel):
    id: Optional[str] = None
    user_id: str
    intent: str
    topic: Optional[str] = None
    grade: int
    subject: str
    language: str
    content_json: dict = Field(default_factory=dict)
    rating: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScheduledClass(BaseModel):
    id: Optional[str] = None
    user_id: str
    grade: int
    subject: str
    class_number: int
    chapter: str
    focus: str = ""
    scheduled_date: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
