from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from auth import models  # noqa: F401
from auth.models import Role, User
from auth.security import create_token, hash_password
from db import engine
from sqlmodel import Session


def _admin_token(email="sched-admin@example.com"):
    with Session(engine) as db:
        admin = User(email=email, password_hash=hash_password("pw"), role=Role.admin, name="Admin")
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return create_token(admin.id, "admin")


def _teacher_with_schedule(client, email, chapter="Ch1", days_ahead=1):
    signup = client.post(
        "/api/auth/signup", json={"email": email, "password": "pw", "name": f"T-{email[:6]}"}
    )
    token = signup.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 9, "subject": "science", "content": "Ch1\nCh2"},
        headers=headers,
    )
    target = date.today() + timedelta(days=days_ahead)
    with patch(
        "auth.routes.generate_schedule",
        new=AsyncMock(return_value=[{"chapter": chapter, "focus": "focus text"}]),
    ):
        client.post(
            "/api/auth/me/schedule/generate",
            json={
                "grade": 9,
                "subject": "science",
                "start_date": target.isoformat(),
                "end_date": target.isoformat(),
                "classes_per_week": 7,
            },
            headers=headers,
        )
    return token, headers


def test_admin_schedule_requires_admin(client):
    signup = client.post(
        "/api/auth/signup", json={"email": "sched-nonadmin@example.com", "password": "pw", "name": "T"}
    )
    resp = client.get(
        "/api/auth/admin/schedule",
        headers={"Authorization": f"Bearer {signup.json()['token']}"},
    )
    assert resp.status_code == 403


def test_admin_sees_upcoming_classes_across_teachers(client):
    admin = _admin_token("sched-admin-list@example.com")
    _teacher_with_schedule(client, "sched-t1@example.com", chapter="Photosynthesis")

    resp = client.get(
        "/api/auth/admin/schedule", headers={"Authorization": f"Bearer {admin}"}
    )
    assert resp.status_code == 200
    rows = resp.json()
    match = [r for r in rows if r["chapter"] == "Photosynthesis"]
    assert len(match) == 1
    assert match[0]["teacher_name"].startswith("T-")
    assert match[0]["subject"] == "science"


def test_admin_can_edit_a_teachers_class(client):
    admin = _admin_token("sched-admin-edit@example.com")
    _, teacher_headers = _teacher_with_schedule(client, "sched-t2@example.com", chapter="Old Chapter")

    listing = client.get(
        "/api/auth/admin/schedule", headers={"Authorization": f"Bearer {admin}"}
    ).json()
    entry = next(r for r in listing if r["chapter"] == "Old Chapter")

    patch_resp = client.patch(
        f"/api/auth/admin/schedule/{entry['id']}",
        json={"chapter": "New Chapter", "focus": "updated focus"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["chapter"] == "New Chapter"

    # The teacher sees the admin's edit in their own schedule.
    teacher_view = client.get(
        "/api/auth/me/schedule",
        params={"grade": 9, "subject": "science"},
        headers=teacher_headers,
    ).json()
    assert any(r["chapter"] == "New Chapter" for r in teacher_view)


def test_admin_can_add_a_class_for_a_teacher(client):
    admin = _admin_token("sched-admin-add@example.com")
    signup = client.post(
        "/api/auth/signup", json={"email": "sched-t3@example.com", "password": "pw", "name": "Added To"}
    )
    teacher_headers = {"Authorization": f"Bearer {signup.json()['token']}"}
    teacher_id = client.get("/api/auth/me", headers=teacher_headers).json()["id"]

    target = (date.today() + timedelta(days=2)).isoformat()
    resp = client.post(
        "/api/auth/admin/schedule",
        json={
            "teacher_id": teacher_id,
            "grade": 9,
            "subject": "science",
            "chapter": "Admin Added Chapter",
            "focus": "set by admin",
            "scheduled_date": target,
        },
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200

    teacher_view = client.get(
        "/api/auth/me/schedule",
        params={"grade": 9, "subject": "science"},
        headers=teacher_headers,
    ).json()
    assert any(r["chapter"] == "Admin Added Chapter" for r in teacher_view)


def test_admin_can_delete_a_class(client):
    admin = _admin_token("sched-admin-del@example.com")
    _, teacher_headers = _teacher_with_schedule(client, "sched-t4@example.com", chapter="Delete Me")

    listing = client.get(
        "/api/auth/admin/schedule", headers={"Authorization": f"Bearer {admin}"}
    ).json()
    entry = next(r for r in listing if r["chapter"] == "Delete Me")

    resp = client.delete(
        f"/api/auth/admin/schedule/{entry['id']}",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200

    teacher_view = client.get(
        "/api/auth/me/schedule",
        params={"grade": 9, "subject": "science"},
        headers=teacher_headers,
    ).json()
    assert not any(r["chapter"] == "Delete Me" for r in teacher_view)
