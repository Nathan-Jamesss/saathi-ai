"""Firestore query helpers for the auth/* collections.

Note on indexing: every query here uses only equality (==) filters and
sorts in Python rather than Firestore's order_by(). Firestore auto-indexes
any number of equality filters with zero setup; mixing orderBy() with
filters on a different field requires a manually-created composite index.
Sorting in Python avoids that entirely — our per-user data volumes are
small, so this costs nothing in practice and needs no console setup.
"""
from datetime import datetime, timezone
from typing import List, Optional

from google.cloud.firestore_v1.base_query import FieldFilter

from firestore_db import get_client
from auth.models import Role, ScheduledClass, SessionHistory, Syllabus, User

USERS = "users"
SYLLABUS = "syllabus"
HISTORY = "session_history"
SCHEDULE = "scheduled_classes"


def _user_from_doc(doc) -> Optional[User]:
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return User(**data)


def get_user(user_id: str) -> Optional[User]:
    return _user_from_doc(get_client().collection(USERS).document(user_id).get())


def get_user_by_email(email: str) -> Optional[User]:
    docs = list(
        get_client().collection(USERS).where(filter=FieldFilter("email", "==", email)).limit(1).stream()
    )
    return _user_from_doc(docs[0]) if docs else None


def create_user(user: User) -> User:
    ref = get_client().collection(USERS).document()
    data = user.model_dump(exclude={"id"})
    ref.set(data)
    user.id = ref.id
    return user


def update_user_fields(user_id: str, fields: dict) -> None:
    get_client().collection(USERS).document(user_id).update(fields)


def list_teachers() -> List[User]:
    docs = get_client().collection(USERS).where(filter=FieldFilter("role", "==", Role.teacher.value)).stream()
    return [_user_from_doc(d) for d in docs]


def count_sessions_for_user(user_id: str) -> int:
    query = get_client().collection(HISTORY).where(filter=FieldFilter("user_id", "==", user_id))
    result = query.count().get()
    return int(result[0][0].value)


def _syllabus_doc_id(user_id: str, grade: int, subject: str) -> str:
    return f"{user_id}_{grade}_{subject}"


def get_syllabus(user_id: str, grade: int, subject: str) -> Optional[Syllabus]:
    doc = get_client().collection(SYLLABUS).document(_syllabus_doc_id(user_id, grade, subject)).get()
    if not doc.exists:
        return None
    return Syllabus(**doc.to_dict())


def save_syllabus(user_id: str, grade: int, subject: str, content: str) -> Syllabus:
    syllabus = Syllabus(
        user_id=user_id, grade=grade, subject=subject, content=content,
        updated_at=datetime.now(timezone.utc),
    )
    get_client().collection(SYLLABUS).document(_syllabus_doc_id(user_id, grade, subject)).set(
        syllabus.model_dump()
    )
    return syllabus


def save_history(entry: SessionHistory) -> SessionHistory:
    ref = get_client().collection(HISTORY).document()
    ref.set(entry.model_dump(exclude={"id"}))
    entry.id = ref.id
    return entry


def list_history(user_id: str) -> List[SessionHistory]:
    docs = get_client().collection(HISTORY).where(filter=FieldFilter("user_id", "==", user_id)).stream()
    rows = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        rows.append(SessionHistory(**data))
    rows.sort(key=lambda r: r.created_at, reverse=True)
    return rows


def create_scheduled_classes(rows: List[ScheduledClass]) -> List[ScheduledClass]:
    batch = get_client().batch()
    coll = get_client().collection(SCHEDULE)
    created = []
    for row in rows:
        ref = coll.document()
        batch.set(ref, row.model_dump(exclude={"id"}))
        row.id = ref.id
        created.append(row)
    batch.commit()
    return created


def delete_schedule_for(user_id: str, grade: int, subject: str) -> None:
    docs = (
        get_client()
        .collection(SCHEDULE)
        .where(filter=FieldFilter("user_id", "==", user_id))
        .where(filter=FieldFilter("grade", "==", grade))
        .where(filter=FieldFilter("subject", "==", subject))
        .stream()
    )
    batch = get_client().batch()
    for d in docs:
        batch.delete(d.reference)
    batch.commit()


def list_schedule(user_id: str, grade: int, subject: str) -> List[ScheduledClass]:
    docs = (
        get_client()
        .collection(SCHEDULE)
        .where(filter=FieldFilter("user_id", "==", user_id))
        .where(filter=FieldFilter("grade", "==", grade))
        .where(filter=FieldFilter("subject", "==", subject))
        .stream()
    )
    rows = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        rows.append(ScheduledClass(**data))
    rows.sort(key=lambda r: r.scheduled_date)
    return rows


def get_scheduled_class(entry_id: str) -> Optional[ScheduledClass]:
    doc = get_client().collection(SCHEDULE).document(entry_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return ScheduledClass(**data)


def delete_scheduled_class(entry_id: str) -> None:
    get_client().collection(SCHEDULE).document(entry_id).delete()
