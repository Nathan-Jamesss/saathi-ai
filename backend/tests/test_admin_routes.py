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
