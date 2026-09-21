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
