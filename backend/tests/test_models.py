from auth import firestore_repo
from auth.models import User, SessionHistory, Role


def test_create_and_query_user(client):
    user = User(
        email="teacher1@example.com",
        password_hash="hashed",
        role=Role.teacher,
        name="Test Teacher",
    )
    firestore_repo.create_user(user)

    found = firestore_repo.get_user_by_email("teacher1@example.com")
    assert found is not None
    assert found.role == Role.teacher
    assert found.is_active is True


def test_session_history_links_to_user(client):
    user = firestore_repo.create_user(User(
        email="teacher2@example.com",
        password_hash="hashed",
        role=Role.teacher,
        name="Test Teacher 2",
    ))

    entry = firestore_repo.save_history(SessionHistory(
        user_id=user.id,
        intent="concept_simplification",
        topic="photosynthesis",
        grade=10,
        subject="science",
        language="en",
        content_json={"explanation": "..."},
    ))

    assert entry.id is not None
    assert entry.user_id == user.id
    assert entry.content_json["explanation"] == "..."
