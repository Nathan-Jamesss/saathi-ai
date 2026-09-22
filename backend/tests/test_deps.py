from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth import firestore_repo
from auth.models import User, Role
from auth.security import hash_password, create_token
from auth.deps import get_current_user, require_admin, get_optional_user

_test_app = FastAPI()


@_test_app.get("/whoami")
def whoami(user=Depends(get_current_user)):
    return {"id": user.id, "role": user.role.value}


@_test_app.get("/admin-only")
def admin_only(user=Depends(require_admin)):
    return {"ok": True}


@_test_app.get("/optional")
def optional(user=Depends(get_optional_user)):
    return {"logged_in": user is not None}


def _make_user(role: Role, email: str) -> User:
    user = User(email=email, password_hash=hash_password("pw"), role=role, name="X")
    return firestore_repo.create_user(user)


def test_get_current_user_requires_token():
    c = TestClient(_test_app)
    resp = c.get("/whoami")
    assert resp.status_code == 401


def test_get_current_user_accepts_valid_token():
    user = _make_user(Role.teacher, "deps-teacher@example.com")
    token = create_token(user.id, user.role.value)
    c = TestClient(_test_app)
    resp = c.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "teacher"


def test_require_admin_rejects_teacher():
    user = _make_user(Role.teacher, "deps-teacher2@example.com")
    token = create_token(user.id, user.role.value)
    c = TestClient(_test_app)
    resp = c.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_require_admin_accepts_admin():
    user = _make_user(Role.admin, "deps-admin@example.com")
    token = create_token(user.id, user.role.value)
    c = TestClient(_test_app)
    resp = c.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_optional_user_no_token_is_none():
    c = TestClient(_test_app)
    resp = c.get("/optional")
    assert resp.json() == {"logged_in": False}


def test_deactivated_user_rejected():
    user = _make_user(Role.teacher, "deps-inactive@example.com")
    token = create_token(user.id, user.role.value)
    firestore_repo.update_user_fields(user.id, {"is_active": False})
    c = TestClient(_test_app)
    resp = c.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
