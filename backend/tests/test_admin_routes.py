from unittest.mock import AsyncMock, patch

from sqlmodel import Session

from db import engine
from auth.models import User, Role
from auth.security import hash_password, create_token


def _make_admin_token(email="admin-routes@example.com"):
    with Session(engine) as db:
        admin = User(email=email, password_hash=hash_password("pw"), role=Role.admin, name="Admin")
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return create_token(admin.id, "admin")


def test_admin_can_create_teacher(client):
    token = _make_admin_token()
    resp = client.post(
        "/api/auth/admin/teachers",
        json={"email": "created-by-admin@example.com", "password": "pw", "name": "T"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "created-by-admin@example.com"
    assert body["is_active"] is True
    assert body["session_count"] == 0


def test_teacher_cannot_create_teacher(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "not-admin@example.com", "password": "pw", "name": "T"},
    )
    token = signup.json()["token"]
    resp = client.post(
        "/api/auth/admin/teachers",
        json={"email": "x@example.com", "password": "pw", "name": "X"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_admin_can_list_teachers(client):
    token = _make_admin_token("admin-list@example.com")
    client.post(
        "/api/auth/admin/teachers",
        json={"email": "listed-teacher@example.com", "password": "pw", "name": "T"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get(
        "/api/auth/admin/teachers", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    emails = [t["email"] for t in resp.json()]
    assert "listed-teacher@example.com" in emails


def test_admin_can_deactivate_teacher(client):
    token = _make_admin_token("admin-patch@example.com")
    create = client.post(
        "/api/auth/admin/teachers",
        json={"email": "to-deactivate@example.com", "password": "pw", "name": "T"},
        headers={"Authorization": f"Bearer {token}"},
    )
    teacher_id = create.json()["id"]

    patch = client.patch(
        f"/api/auth/admin/teachers/{teacher_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200
    assert patch.json()["is_active"] is False

    login = client.post(
        "/api/auth/login",
        json={"email": "to-deactivate@example.com", "password": "pw"},
    )
    assert login.status_code == 403


def test_teacher_cannot_list_teachers(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "list-non-admin@example.com", "password": "pw", "name": "T"},
    )
    token = signup.json()["token"]
    resp = client.get(
        "/api/auth/admin/teachers", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_teacher_cannot_patch_teacher(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "patch-non-admin@example.com", "password": "pw", "name": "T"},
    )
    token = signup.json()["token"]
    resp = client.patch(
        "/api/auth/admin/teachers/1",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_admin_overview_requires_admin(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "overview-non-admin@example.com", "password": "pw", "name": "T"},
    )
    token = signup.json()["token"]
    resp = client.get(
        "/api/auth/admin/overview", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_admin_overview_counts_teachers_sessions_and_coverage(client):
    admin_token = _make_admin_token("admin-overview@example.com")

    signup = client.post(
        "/api/auth/signup",
        json={"email": "overview-teacher@example.com", "password": "pw", "name": "Overview Teacher"},
    )
    teacher_token = signup.json()["token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 9, "subject": "science", "content": "Ch1"},
        headers=teacher_headers,
    )

    with patch(
        "api.process.route_intent",
        new=AsyncMock(
            return_value={
                "intent": "concept_simplification",
                "topic": "motion",
                "grade": 9,
                "subject": "science",
                "language": "en",
                "confidence": 0.9,
            }
        ),
    ), patch(
        "api.process.generate_concept",
        new=AsyncMock(return_value={"explanation": "things move"}),
    ):
        client.post(
            "/api/process",
            json={"transcript": "explain motion", "session": {}, "regenerate": False},
            headers=teacher_headers,
        )

    resp = client.get(
        "/api/auth/admin/overview", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_teachers"] >= 1
    assert body["active_teachers"] >= 1
    assert body["total_sessions"] >= 1
    assert isinstance(body["total_scheduled_classes"], int)

    cell = next(c for c in body["coverage"] if c["grade"] == 9 and c["subject"] == "science")
    assert "Overview Teacher" in cell["teachers"]

    empty_cell = next(c for c in body["coverage"] if c["grade"] == 12 and c["subject"] == "english")
    assert empty_cell["teachers"] == []


def test_admin_teacher_list_includes_last_active(client):
    admin_token = _make_admin_token("admin-lastactive@example.com")

    signup = client.post(
        "/api/auth/signup",
        json={"email": "never-active@example.com", "password": "pw", "name": "Never Active"},
    )
    resp = client.get(
        "/api/auth/admin/teachers", headers={"Authorization": f"Bearer {admin_token}"}
    )
    teacher = next(t for t in resp.json() if t["email"] == "never-active@example.com")
    assert teacher["last_active"] is None

    teacher_token = signup.json()["token"]
    with patch(
        "api.process.route_intent",
        new=AsyncMock(
            return_value={
                "intent": "concept_simplification",
                "topic": "x",
                "grade": 10,
                "subject": "science",
                "language": "en",
                "confidence": 0.9,
            }
        ),
    ), patch(
        "api.process.generate_concept",
        new=AsyncMock(return_value={"explanation": "x"}),
    ):
        client.post(
            "/api/process",
            json={"transcript": "explain x", "session": {}, "regenerate": False},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

    resp2 = client.get(
        "/api/auth/admin/teachers", headers={"Authorization": f"Bearer {admin_token}"}
    )
    teacher2 = next(t for t in resp2.json() if t["email"] == "never-active@example.com")
    assert teacher2["last_active"] is not None
