from sqlmodel import Session, select

from db import engine
from auth.models import User, SessionHistory, Role


def test_create_and_query_user(client):
    with Session(engine) as db:
        user = User(
            email="teacher1@example.com",
            password_hash="hashed",
            role=Role.teacher,
            name="Test Teacher",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        found = db.exec(select(User).where(User.email == "teacher1@example.com")).first()
        assert found is not None
        assert found.role == Role.teacher
        assert found.is_active is True


def test_session_history_links_to_user(client):
    with Session(engine) as db:
        user = User(
            email="teacher2@example.com",
            password_hash="hashed",
            role=Role.teacher,
            name="Test Teacher 2",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        entry = SessionHistory(
            user_id=user.id,
            intent="concept_simplification",
            topic="photosynthesis",
            grade=10,
            subject="science",
            language="en",
            content_json={"explanation": "..."},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        assert entry.id is not None
        assert entry.user_id == user.id
        assert entry.content_json["explanation"] == "..."
