from sqlmodel import Session, select

from db import engine
from auth.models import User


def test_signup_creates_teacher_and_ignores_role_override(client):
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": "new-teacher@example.com",
            "password": "s3cret!",
            "name": "New Teacher",
            "role": "admin",  # must be ignored — server forces teacher
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "teacher"
    assert "token" in body


def test_signup_rejects_duplicate_email(client):
    client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "password": "pw", "name": "A"},
    )
    resp = client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "password": "pw", "name": "B"},
    )
    assert resp.status_code == 400


def test_login_success(client):
    client.post(
        "/api/auth/signup",
        json={"email": "login-me@example.com", "password": "correct-pw", "name": "L"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login-me@example.com", "password": "correct-pw"},
    )
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client):
    client.post(
        "/api/auth/signup",
        json={"email": "login-wrong@example.com", "password": "correct-pw", "name": "L"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login-wrong@example.com", "password": "bad-pw"},
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_profile(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "me-profile@example.com", "password": "pw", "name": "Me"},
    )
    token = signup.json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me-profile@example.com"


def test_login_rejects_deactivated_user(client):
    client.post(
        "/api/auth/signup",
        json={"email": "deactivated@example.com", "password": "correct-pw", "name": "D"},
    )
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == "deactivated@example.com")
        ).first()
        user.is_active = False
        session.add(user)
        session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"email": "deactivated@example.com", "password": "correct-pw"},
    )
    assert resp.status_code == 403
