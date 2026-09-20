# Auth, Roles & Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JWT-based teacher/admin auth, a `User`/`SessionHistory` Postgres-backed data layer, teacher self-signup + admin-created accounts, a teacher dashboard (history/resume), and an admin dashboard (teacher management + usage) to Saathi.AI.

**Architecture:** New `backend/auth/` module (SQLModel models, bcrypt+JWT security, FastAPI auth dependencies, routes) sits alongside the existing `backend/api/` and `backend/core/` modules. `backend/db.py` owns a single SQLModel `engine` (defaults to local SQLite for zero-friction dev, `DATABASE_URL` env var points it at Postgres in prod). Existing `/api/process` gains an *optional* auth dependency so it keeps working logged-out (demo-safe) but persists history when a token is present. Frontend gets 4 new static pages (`login.html`, `signup.html`, `dashboard.html`, `admin.html`) plus a new `js/auth.js` module, following the existing vanilla-JS/no-framework, no-build-step pattern.

**Tech Stack:** FastAPI (existing), SQLModel + Alembic (new — Postgres/SQLite ORM + migrations), `passlib[bcrypt]` (password hashing), `pyjwt` (tokens), `psycopg[binary]` (Postgres driver), pytest + `fastapi.testclient` (new — no test suite exists yet).

**Spec:** [docs/superpowers/specs/2026-09-20-auth-roles-dashboard-design.md](../specs/2026-09-20-auth-roles-dashboard-design.md)

## Global Constraints

- Role is always server-assigned on signup — request payload role is ignored (spec §Auth flow).
- JWT expiry: 24h, `HS256`, secret from `JWT_SECRET` env var (spec §Auth flow).
- `/api/process` and `/api/export` stay usable **without** a token — auth is additive, not a hard lock (spec §Existing endpoint changes).
- No email verification, no forgot-password flow in this plan (spec §Non-goals).
- `display.html` gets no auth changes at all (spec §Frontend changes).
- CORS stays `allow_origins="*"`, `allow_credentials=False` — bearer tokens only, never cookies (spec §Deployment).
- Admin accounts are never created via a public API route — only via `scripts/create_admin.py` (spec §Auth flow).

---

## Task 1: Database engine + dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Create: `backend/db.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `db.engine` (SQLModel `Engine`), `db.get_db()` — a generator yielding a `sqlmodel.Session`, used as a FastAPI dependency by every later task.

- [ ] **Step 1: Add new dependencies**

Append to `backend/requirements.txt`:
```
sqlmodel>=0.0.22
alembic>=1.13.2
psycopg[binary]>=3.2.1
pyjwt>=2.9.0
passlib[bcrypt]>=1.7.4
pytest>=8.3.2
```

- [ ] **Step 2: Document new env vars**

Append to `backend/.env.example`:
```

# Postgres connection string (prod). Omit locally to use a SQLite file at ./data/saathi.db
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/saathi

# Secret used to sign JWTs — set a long random value in production
JWT_SECRET=change-me-in-production

# Seed admin account — used once by `python -m scripts.create_admin`
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me
```

- [ ] **Step 3: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`
Expected: installs succeed, no errors.

- [ ] **Step 4: Write `db.py`**

```python
"""Database engine & session dependency"""
import os
from sqlmodel import create_engine, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/saathi.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


def get_db():
    with Session(engine) as session:
        yield session
```

- [ ] **Step 5: Write test setup (`tests/__init__.py`, `tests/conftest.py`)**

`backend/tests/__init__.py`: empty file.

`backend/tests/conftest.py`:
```python
"""Shared test fixtures — an isolated SQLite DB per test session."""
import os
import tempfile

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from db import engine  # noqa: E402
import main as main_module  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    from auth import models  # noqa: F401  (ensures tables are registered)
    SQLModel.metadata.create_all(engine)
    yield
    os.close(_db_fd)
    os.remove(_db_path)


@pytest.fixture()
def client():
    return TestClient(main_module.app)
```

Note: `from auth import models` inside the fixture will fail until Task 2 creates that module — that's expected; this task's own test (Step 6) doesn't need it.

- [ ] **Step 6: Write the failing test**

`backend/tests/test_db.py`:
```python
from sqlmodel import Session
from db import engine


def test_engine_connects():
    with Session(engine) as session:
        result = session.exec("SELECT 1").one()
        assert result == (1,) or result == 1
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd backend && pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth'` (conftest imports `auth.models` inside the autouse fixture) — this is expected per the note in Step 5.

Since Task 2 hasn't run yet, temporarily comment out the `from auth import models` line in `conftest.py` to verify Task 1 in isolation, then restore it (uncommented) as the last action of Task 2 Step 1.

- [ ] **Step 8: Run test to verify it passes (auth import commented out)**

Run: `cd backend && pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/db.py backend/tests/
git commit -m "feat(auth): add SQLModel db engine + test scaffolding"
```

---

## Task 2: User & SessionHistory models

**Files:**
- Create: `backend/auth/__init__.py`
- Create: `backend/auth/models.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `db.engine` (Task 1).
- Produces: `auth.models.Role` (str `Enum`: `teacher`, `admin`), `auth.models.User` (SQLModel table — fields: `id`, `email`, `password_hash`, `role`, `name`, `school`, `grade_default`, `subject_default`, `is_active`, `created_at`), `auth.models.SessionHistory` (SQLModel table — fields: `id`, `user_id`, `intent`, `topic`, `grade`, `subject`, `language`, `content_json` (dict), `rating`, `created_at`).

- [ ] **Step 1: Restore the conftest import**

In `backend/tests/conftest.py`, uncomment (or leave in place) the `from auth import models  # noqa: F401` line inside `_create_tables` — it now has something to import.

- [ ] **Step 2: Write `auth/__init__.py`**

Empty file: `backend/auth/__init__.py`.

- [ ] **Step 3: Write the failing test**

`backend/tests/test_models.py`:
```python
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
```

(The `client` fixture parameter is unused directly but pulls in the session-scoped `_create_tables` fixture dependency chain via app import — keep it so table creation has run.)

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.models'`

- [ ] **Step 5: Write `auth/models.py`**

```python
"""User & session-history database models"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, JSON
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/auth/ backend/tests/
git commit -m "feat(auth): add User and SessionHistory models"
```

---

## Task 3: Password hashing & JWT

**Files:**
- Create: `backend/auth/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `auth.security.hash_password(password: str) -> str`, `auth.security.verify_password(password: str, password_hash: str) -> bool`, `auth.security.create_token(user_id: int, role: str) -> str`, `auth.security.decode_token(token: str) -> dict` (raises on invalid/expired — callers catch `Exception`).

- [ ] **Step 1: Write the failing test**

`backend/tests/test_security.py`:
```python
import time

import jwt
import pytest

from auth.security import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token():
    token = create_token(user_id=42, role="teacher")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "teacher"


def test_decode_rejects_expired_token():
    expired = jwt.encode(
        {"sub": "1", "role": "teacher", "exp": int(time.time()) - 10},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.security'`

- [ ] **Step 3: Write `auth/security.py`**

```python
"""Password hashing & JWT issuance/verification"""
import os
import time

import jwt
from passlib.context import CryptContext

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 24 * 60 * 60


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_ctx.verify(password, password_hash)


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/auth/security.py backend/tests/test_security.py
git commit -m "feat(auth): add password hashing and JWT helpers"
```

---

## Task 4: Auth dependencies (get_current_user, require_teacher, require_admin)

**Files:**
- Create: `backend/auth/deps.py`
- Test: `backend/tests/test_deps.py`

**Interfaces:**
- Consumes: `db.get_db` (Task 1), `auth.models.User`/`Role` (Task 2), `auth.security.decode_token` (Task 3).
- Produces: `auth.deps.get_optional_user(...) -> Optional[User]`, `auth.deps.get_current_user(...) -> User` (raises `HTTPException(401)`), `auth.deps.require_teacher(...) -> User` (raises `HTTPException(403)`), `auth.deps.require_admin(...) -> User` (raises `HTTPException(403)`). All four are FastAPI dependency callables — later tasks use them via `Depends(...)`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_deps.py`:
```python
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from db import engine, get_db
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
    with Session(engine) as db:
        user = User(email=email, password_hash=hash_password("pw"), role=role, name="X")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


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
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        db_user.is_active = False
        db.add(db_user)
        db.commit()
    c = TestClient(_test_app)
    resp = c.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_deps.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.deps'`

- [ ] **Step 3: Write `auth/deps.py`**

```python
"""FastAPI auth dependencies"""
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from db import get_db
from auth.models import Role, User
from auth.security import decode_token


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        return None
    return user


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.teacher:
        raise HTTPException(status_code=403, detail="Teacher role required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_deps.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/auth/deps.py backend/tests/test_deps.py
git commit -m "feat(auth): add get_current_user/require_teacher/require_admin dependencies"
```

---

## Task 5: Signup, login, and /me routes

**Files:**
- Create: `backend/auth/routes.py`
- Test: `backend/tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `db.get_db`, `auth.models.{User,Role}`, `auth.security.{hash_password,verify_password,create_token}`, `auth.deps.get_current_user`.
- Produces: `auth.routes.router` (an `APIRouter` with prefix `/auth`) — mounted onto the app in Task 10. Endpoints: `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_auth_routes.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth_routes.py -v`
Expected: FAIL — 404s (route doesn't exist / router not mounted yet). This task defines the router; Task 10 mounts it. Mount it provisionally now in `tests/conftest.py`... **no** — instead, this task's test imports the real `main_module.app` via the `client` fixture, so mounting must happen for these tests to ever pass. To keep TDD honest without duplicating work, do the router mount as the last step of *this* task (Step 5 below), not Task 10 — Task 10 will only add the remaining admin routes' router (same router object, already mounted) and the final wiring check.

- [ ] **Step 3: Write `auth/routes.py` (signup/login/me only for now)**

```python
"""Auth routes: signup, login, profile"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from db import get_db
from auth.models import Role, User
from auth.security import create_token, hash_password, verify_password
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    school: Optional[str] = None
    grade_default: int = 10
    subject_default: str = "science"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    role: str
    name: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    school: Optional[str]
    grade_default: int
    subject_default: str


@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.exec(select(User).where(User.email == req.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=Role.teacher,
        name=req.name,
        school=req.school,
        grade_default=req.grade_default,
        subject_default=req.subject_default,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id, user.role.value)
    return TokenResponse(token=token, role=user.role.value, name=user.name)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.email == req.email)).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    token = create_token(user.id, user.role.value)
    return TokenResponse(token=token, role=user.role.value, name=user.name)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        school=user.school,
        grade_default=user.grade_default,
        subject_default=user.subject_default,
    )
```

- [ ] **Step 4: Mount the router in `backend/main.py`**

In `backend/main.py`, add the import alongside the existing routers:
```python
from auth.routes import router as auth_router
```
And add the include alongside the existing `app.include_router(...)` calls:
```python
app.include_router(auth_router, prefix="/api")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_auth_routes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Run full suite to check no regressions**

Run: `cd backend && pytest -v`
Expected: all prior tests (Tasks 1-4) plus these 6 pass.

- [ ] **Step 7: Commit**

```bash
git add backend/auth/routes.py backend/main.py backend/tests/test_auth_routes.py
git commit -m "feat(auth): add signup, login, and /me routes"
```

---

## Task 6: Session history persistence wired into /api/process

**Files:**
- Modify: `backend/api/process.py`
- Create: `backend/auth/routes.py` additions (`GET /auth/me/history`) — same file as Task 5
- Test: `backend/tests/test_process_history.py`

**Interfaces:**
- Consumes: `auth.deps.get_optional_user`, `db.get_db`, `auth.models.SessionHistory`.
- Produces: every authenticated `/api/process` call now writes a `SessionHistory` row; `GET /api/auth/me/history` returns that user's rows newest-first.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_process_history.py`:
```python
from unittest.mock import AsyncMock, patch


def _signup(client, email):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "pw", "name": "Hist Teacher"},
    )
    return resp.json()["token"]


def test_process_without_token_still_works(client):
    with patch(
        "api.process.route_intent",
        new=AsyncMock(return_value={"intent": "unclear", "confidence": 0.0, "language": "en"}),
    ):
        resp = client.post(
            "/api/process",
            json={"transcript": "asdkjasldkj", "session": {}, "regenerate": False},
        )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "unclear"


def test_process_with_token_saves_history(client):
    token = _signup(client, "hist1@example.com")

    with patch(
        "api.process.route_intent",
        new=AsyncMock(
            return_value={
                "intent": "concept_simplification",
                "topic": "photosynthesis",
                "grade": 10,
                "subject": "science",
                "language": "en",
                "confidence": 0.9,
            }
        ),
    ), patch(
        "api.process.generate_concept",
        new=AsyncMock(return_value={"explanation": "plants make food"}),
    ):
        resp = client.post(
            "/api/process",
            json={"transcript": "explain photosynthesis", "session": {}, "regenerate": False},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    history = client.get(
        "/api/auth/me/history", headers={"Authorization": f"Bearer {token}"}
    )
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 1
    assert rows[0]["topic"] == "photosynthesis"
    assert rows[0]["content_json"]["explanation"] == "plants make food"


def test_process_without_token_does_not_save_history(client):
    with patch(
        "api.process.route_intent",
        new=AsyncMock(
            return_value={
                "intent": "concept_simplification",
                "topic": "gravity",
                "grade": 10,
                "subject": "science",
                "language": "en",
                "confidence": 0.9,
            }
        ),
    ), patch(
        "api.process.generate_concept",
        new=AsyncMock(return_value={"explanation": "things fall down"}),
    ):
        resp = client.post(
            "/api/process",
            json={"transcript": "explain gravity", "session": {}, "regenerate": False},
        )
    assert resp.status_code == 200

    token = _signup(client, "hist2@example.com")
    history = client.get(
        "/api/auth/me/history", headers={"Authorization": f"Bearer {token}"}
    )
    assert history.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_process_history.py -v`
Expected: FAIL — `/api/auth/me/history` 404s, and `test_process_with_token_saves_history` fails on that call.

- [ ] **Step 3: Add `GET /auth/me/history` to `auth/routes.py`**

Add imports at top of `backend/auth/routes.py`:
```python
from typing import List

from auth.models import SessionHistory
```

Append to `backend/auth/routes.py`:
```python
class HistoryEntry(BaseModel):
    id: int
    intent: str
    topic: Optional[str]
    grade: int
    subject: str
    language: str
    content_json: dict
    rating: int
    created_at: str


@router.get("/me/history", response_model=List[HistoryEntry])
def my_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.exec(
        select(SessionHistory)
        .where(SessionHistory.user_id == user.id)
        .order_by(SessionHistory.created_at.desc())
    ).all()
    return [
        HistoryEntry(
            id=r.id,
            intent=r.intent,
            topic=r.topic,
            grade=r.grade,
            subject=r.subject,
            language=r.language,
            content_json=r.content_json,
            rating=r.rating,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
```

- [ ] **Step 4: Wire optional-auth history saving into `backend/api/process.py`**

Modify `backend/api/process.py`. The file currently starts with:
```python
from fastapi import APIRouter, HTTPException
```
Change this line to add `Depends` (not present yet in this file):
```python
from fastapi import APIRouter, Depends, HTTPException
```

Then add the rest of the new imports below the existing ones:
```python
from typing import Optional as OptionalType

from sqlmodel import Session

from db import get_db
from auth.deps import get_optional_user
from auth.models import SessionHistory, User
```

Change the route signature (currently `async def process(req: ProcessRequest):`) to:
```python
@router.post("/process")
async def process(
    req: ProcessRequest,
    user: OptionalType[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
```

Replace the two `return {...}` statements at the end of the function with a single `result` variable built the same way, then a save-and-return block. The "unclear" early return becomes:
```python
    if intent == "unclear" or confidence < 0.45:
        return {
            "intent": "unclear",
            "detected_language": language,
            "topic": None,
            "grade": grade,
            "subject": subject,
            "content": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": str(uuid.uuid4()),
        }
```
— unchanged (unclear results are never saved to history).

The final block (after the `if intent == ...` / `elif` dispatch chain) changes from:
```python
    return {
        "intent": intent,
        "detected_language": language,
        "topic": topic,
        "grade": grade,
        "subject": subject,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(uuid.uuid4()),
    }
```
to:
```python
    result = {
        "intent": intent,
        "detected_language": language,
        "topic": topic,
        "grade": grade,
        "subject": subject,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(uuid.uuid4()),
    }

    if user:
        db.add(
            SessionHistory(
                user_id=user.id,
                intent=intent,
                topic=topic,
                grade=grade,
                subject=subject,
                language=language,
                content_json=content,
                rating=0,
            )
        )
        db.commit()

    return result
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_process_history.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Run full suite to check no regressions**

Run: `cd backend && pytest -v`
Expected: all tests from Tasks 1-6 pass.

- [ ] **Step 7: Commit**

```bash
git add backend/auth/routes.py backend/api/process.py backend/tests/test_process_history.py
git commit -m "feat(auth): persist session history for logged-in users on /api/process"
```

---

## Task 7: Admin routes (create/list/patch teachers)

**Files:**
- Modify: `backend/auth/routes.py`
- Test: `backend/tests/test_admin_routes.py`

**Interfaces:**
- Consumes: `auth.deps.require_admin`.
- Produces: `POST /api/auth/admin/teachers`, `GET /api/auth/admin/teachers`, `PATCH /api/auth/admin/teachers/{id}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_admin_routes.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_admin_routes.py -v`
Expected: FAIL — 404s, admin routes don't exist yet.

- [ ] **Step 3: Add admin routes to `auth/routes.py`**

Add import at top of `backend/auth/routes.py`:
```python
from auth.deps import get_current_user, require_admin
```
(replace the existing `from auth.deps import get_current_user` line with this combined one).

Append to `backend/auth/routes.py`:
```python
class TeacherCreateRequest(BaseModel):
    email: str
    password: str
    name: str
    school: Optional[str] = None


class TeacherResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    session_count: int


class TeacherPatchRequest(BaseModel):
    is_active: bool


def _teacher_response(db: Session, teacher: User) -> TeacherResponse:
    count = len(
        db.exec(
            select(SessionHistory).where(SessionHistory.user_id == teacher.id)
        ).all()
    )
    return TeacherResponse(
        id=teacher.id,
        email=teacher.email,
        name=teacher.name,
        is_active=teacher.is_active,
        session_count=count,
    )


@router.post("/admin/teachers", response_model=TeacherResponse)
def admin_create_teacher(
    req: TeacherCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.exec(select(User).where(User.email == req.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    teacher = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=Role.teacher,
        name=req.name,
        school=req.school,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _teacher_response(db, teacher)


@router.get("/admin/teachers", response_model=List[TeacherResponse])
def admin_list_teachers(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    teachers = db.exec(select(User).where(User.role == Role.teacher)).all()
    return [_teacher_response(db, t) for t in teachers]


@router.patch("/admin/teachers/{teacher_id}", response_model=TeacherResponse)
def admin_patch_teacher(
    teacher_id: int,
    req: TeacherPatchRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.get(User, teacher_id)
    if not teacher or teacher.role != Role.teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher.is_active = req.is_active
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _teacher_response(db, teacher)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_admin_routes.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run full suite to check no regressions**

Run: `cd backend && pytest -v`
Expected: all tests from Tasks 1-7 pass.

- [ ] **Step 6: Commit**

```bash
git add backend/auth/routes.py backend/tests/test_admin_routes.py
git commit -m "feat(auth): add admin routes for teacher management"
```

---

## Task 8: Admin seed script

**Files:**
- Create: `backend/scripts/create_admin.py`

**Interfaces:**
- Consumes: `db.engine`, `auth.models.{User,Role}`, `auth.security.hash_password`.
- Produces: a runnable script, `python -m scripts.create_admin`, not exposed via any API route.

- [ ] **Step 1: Write `scripts/create_admin.py`**

```python
"""One-time admin account seed script.

Run from the backend/ directory:
    python -m scripts.create_admin
Reads ADMIN_EMAIL / ADMIN_PASSWORD from the environment (.env locally,
Render env vars in production).
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from sqlmodel import Session, select  # noqa: E402

from db import engine  # noqa: E402
from auth.models import Role, User  # noqa: E402
from auth.security import hash_password  # noqa: E402


def main():
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD must be set in the environment.")
        sys.exit(1)

    with Session(engine) as db:
        existing = db.exec(select(User).where(User.email == email)).first()
        if existing:
            print(f"Admin {email} already exists (id={existing.id}).")
            return
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role=Role.admin,
            name="Admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Created admin {email} (id={admin.id}).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manual test — run it twice**

Run (from `backend/`, with `ADMIN_EMAIL`/`ADMIN_PASSWORD` set in `.env` or exported):
```bash
python -m scripts.create_admin
python -m scripts.create_admin
```
Expected: first run prints `Created admin ...`; second run prints `Admin ... already exists ...` (idempotent, no duplicate row / crash).

- [ ] **Step 3: Manual test — log in as the seeded admin**

Run: `curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"<ADMIN_EMAIL>\",\"password\":\"<ADMIN_PASSWORD>\"}"`
Expected: `200` with `{"token": "...", "role": "admin", "name": "Admin"}`.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/create_admin.py
git commit -m "feat(auth): add admin account seed script"
```

---

## Task 9: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_initial_auth_tables.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `auth.models` (for autogenerate metadata).
- Produces: `alembic upgrade head` creates the `user` and `sessionhistory` tables against whatever `DATABASE_URL` points at (Postgres in prod, SQLite locally).

- [ ] **Step 1: Initialize Alembic**

Run (from `backend/`): `alembic init migrations`
Expected: creates `backend/alembic.ini` and `backend/migrations/` (with `env.py`, `script.py.mako`, `versions/`).

- [ ] **Step 2: Point Alembic at `DATABASE_URL` and the SQLModel metadata**

Edit `backend/migrations/env.py`. Near the top, after the existing `from alembic import context` line, add:
```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from sqlmodel import SQLModel

import auth.models  # noqa: F401  (registers tables on SQLModel.metadata)

target_metadata = SQLModel.metadata
```
Replace the line `target_metadata = None` (already present from `alembic init`) by deleting it — the assignment above replaces it.

Find the `config.set_main_option("sqlalchemy.url", ...)` pattern is NOT present by default; instead Alembic reads `sqlalchemy.url` from `alembic.ini`. Since we want it to come from the environment instead, add this right after `target_metadata = SQLModel.metadata`:
```python
config.set_main_option(
    "sqlalchemy.url", os.environ.get("DATABASE_URL", "sqlite:///./data/saathi.db")
)
```

- [ ] **Step 3: Generate the initial migration**

Run (from `backend/`): `alembic revision --autogenerate -m "initial auth tables"`
Expected: creates `backend/migrations/versions/<hash>_initial_auth_tables.py` containing `op.create_table("user", ...)` and `op.create_table("sessionhistory", ...)`.

- [ ] **Step 4: Rename the generated file for a stable, readable name**

Rename the generated `backend/migrations/versions/<hash>_initial_auth_tables.py` to `backend/migrations/versions/0001_initial_auth_tables.py` (keep the `revision = "<hash>"` value inside the file unchanged — only the filename changes).

- [ ] **Step 5: Apply the migration locally**

Run (from `backend/`): `alembic upgrade head`
Expected: no errors; a `data/saathi.db` SQLite file is created (or your local Postgres, if `DATABASE_URL` is set) with `user` and `sessionhistory` tables.

- [ ] **Step 6: Verify tables exist**

Run: `python -c "from sqlmodel import Session, select; from db import engine; from auth.models import User; Session(engine).exec(select(User)).all(); print('ok')"`
Expected: prints `ok` with no errors.

- [ ] **Step 7: Keep `create_all` as a dev-safety net in `main.py`**

In `backend/main.py`, add to the `lifespan` function (so a fresh clone without a migration run still works locally):
```python
from sqlmodel import SQLModel
from db import engine
import auth.models  # noqa: F401
```
at the top with the other imports, and inside `lifespan`, before `init_chroma()`:
```python
SQLModel.metadata.create_all(engine)
```
This is idempotent (`CREATE TABLE IF NOT EXISTS` semantics) and never conflicts with Alembic-managed schemas — Alembic remains authoritative for production migrations (e.g. later column changes in phase 2), this line just prevents "table doesn't exist" on a fresh local SQLite file.

- [ ] **Step 8: Run full test suite to check no regressions**

Run: `cd backend && pytest -v`
Expected: all tests from Tasks 1-8 pass.

- [ ] **Step 9: Commit**

```bash
git add backend/alembic.ini backend/migrations/ backend/main.py
git commit -m "feat(auth): add Alembic migrations for auth tables"
```

---

## Task 10: Render deployment config

**Files:**
- Modify: `render.yaml`

**Interfaces:**
- Consumes: nothing new — this task only changes deployment config, no code interfaces.

- [ ] **Step 1: Add new env vars and migration step to `render.yaml`**

Modify `backend/render.yaml`... — actually the file is at repo root: `render.yaml`. Update `buildCommand` and `envVars`:
```yaml
services:
  - type: web
    name: saathi-ai-backend
    runtime: python
    rootDir: backend
    plan: free
    buildCommand: pip install -r requirements.txt && alembic upgrade head
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GEMINI_API_KEYS
        sync: false            # set in Render dashboard (secret)
      - key: CHROMA_PERSIST_DIR
        value: ./data/chroma
      - key: DATABASE_URL
        sync: false            # set in Render dashboard — Postgres connection string
      - key: JWT_SECRET
        sync: false            # set in Render dashboard (secret, long random value)
      - key: ADMIN_EMAIL
        sync: false            # set in Render dashboard — used once by create_admin.py
      - key: ADMIN_PASSWORD
        sync: false            # set in Render dashboard — used once by create_admin.py
      - key: PYTHON_VERSION
        value: "3.11"
```

- [ ] **Step 2: Commit**

```bash
git add render.yaml
git commit -m "chore(deploy): add auth env vars and migration step to Render config"
```

*(No further action here — actually provisioning the Postgres instance and setting the Render dashboard secrets is a manual deploy-time step for you, covered in the final "What you still need to do" note at the end of this plan.)*

---

## Task 11: Frontend auth module

**Files:**
- Create: `frontend/js/auth.js`

**Interfaces:**
- Produces: `signup({email,password,name,school?}) -> Promise<{token,role,name}>`, `login({email,password}) -> Promise<{token,role,name}>`, `logout()`, `getToken() -> string|null`, `getRole() -> string|null`, `authFetch(path, options) -> Promise<Response>` (adds `Authorization` header automatically, prefixes `BACKEND_URL`), `requireAuth(expectedRole?)` (redirects to `login.html` if no token, or to the correct dashboard if role mismatches).

- [ ] **Step 1: Write `frontend/js/auth.js`**

```javascript
/* auth.js · Login/signup/session-token management */

const TOKEN_KEY = 'saathi-token';
const ROLE_KEY = 'saathi-role';
const NAME_KEY = 'saathi-name';

const BACKEND_URL = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? 'http://localhost:8000'
  : 'https://saathi-ai-hfqi.onrender.com';

function storeSession({ token, role, name }) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
  localStorage.setItem(NAME_KEY, name);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY);
}

export function getName() {
  return localStorage.getItem(NAME_KEY);
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(NAME_KEY);
  location.href = 'login.html';
}

async function _authRequest(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  storeSession(data);
  return data;
}

export function signup({ email, password, name, school }) {
  return _authRequest('/api/auth/signup', { email, password, name, school });
}

export function login({ email, password }) {
  return _authRequest('/api/auth/login', { email, password });
}

export async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(`${BACKEND_URL}${path}`, { ...options, headers });
}

export function requireAuth(expectedRole) {
  const token = getToken();
  if (!token) {
    location.href = 'login.html';
    return false;
  }
  if (expectedRole && getRole() !== expectedRole) {
    location.href = getRole() === 'admin' ? 'admin.html' : 'dashboard.html';
    return false;
  }
  return true;
}
```

- [ ] **Step 2: Manual test**

Serve the frontend locally (`cd frontend && python -m http.server 3000`) with the backend running, open browser devtools console on any page, and run:
```javascript
import('./js/auth.js').then(async (auth) => {
  const result = await auth.signup({ email: `test${Date.now()}@example.com`, password: 'pw123', name: 'Console Test' });
  console.log(result, auth.getToken(), auth.getRole());
});
```
Expected: logs a `{token, role: "teacher", name: "Console Test"}` object, and `getToken()`/`getRole()` return the stored values.

- [ ] **Step 3: Commit**

```bash
git add frontend/js/auth.js
git commit -m "feat(auth): add frontend auth module (login/signup/authFetch)"
```

---

## Task 12: Login and signup pages

**Files:**
- Create: `frontend/login.html`
- Create: `frontend/signup.html`
- Create: `frontend/css/auth.css`

**Interfaces:**
- Consumes: `frontend/js/auth.js` (`login`, `signup`).
- Produces: two standalone pages reachable at `login.html` and `signup.html`, matching the existing `landing.css`/`app.css` visual language (dark theme, Inter Tight font, glass cards — see `frontend/index.html` and `frontend/css/main.css` for the established look).

- [ ] **Step 1: Write `frontend/css/auth.css`**

```css
/* auth.css · Login/signup page styling */

.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
  border-radius: 16px;
  padding: 32px;
  backdrop-filter: blur(12px);
}

.auth-card h1 {
  font-family: 'Inter Tight', sans-serif;
  font-size: 1.5rem;
  margin: 0 0 24px;
}

.auth-field {
  margin-bottom: 16px;
}

.auth-field label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 6px;
  opacity: 0.8;
}

.auth-field input,
.auth-field select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border, rgba(255, 255, 255, 0.15));
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  font-size: 1rem;
  box-sizing: border-box;
}

.auth-submit {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: none;
  background: var(--accent, #6ea8ff);
  color: #0a0a0f;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
}

.auth-error {
  color: #ff6e6e;
  font-size: 0.85rem;
  margin-top: 12px;
  min-height: 1.2em;
}

.auth-switch {
  margin-top: 20px;
  font-size: 0.85rem;
  text-align: center;
  opacity: 0.8;
}

.auth-switch a {
  color: var(--accent, #6ea8ff);
}
```

- [ ] **Step 2: Write `frontend/login.html`**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Saathi.AI · Log in</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/main.css" />
  <link rel="stylesheet" href="css/auth.css" />
</head>
<body>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Log in to Saathi.AI</h1>
      <form id="login-form">
        <div class="auth-field">
          <label for="email">Email</label>
          <input type="email" id="email" required autocomplete="email" />
        </div>
        <div class="auth-field">
          <label for="password">Password</label>
          <input type="password" id="password" required autocomplete="current-password" />
        </div>
        <button type="submit" class="auth-submit">Log in</button>
        <div class="auth-error" id="error"></div>
      </form>
      <div class="auth-switch">
        No account? <a href="signup.html">Sign up</a>
      </div>
    </div>
  </div>

  <script type="module">
    import { login, getRole } from './js/auth.js';

    const form = document.getElementById('login-form');
    const errorEl = document.getElementById('error');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.textContent = '';
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      try {
        await login({ email, password });
        location.href = getRole() === 'admin' ? 'admin.html' : 'dashboard.html';
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 3: Write `frontend/signup.html`**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Saathi.AI · Sign up</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/main.css" />
  <link rel="stylesheet" href="css/auth.css" />
</head>
<body>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Create your teacher account</h1>
      <form id="signup-form">
        <div class="auth-field">
          <label for="name">Name</label>
          <input type="text" id="name" required autocomplete="name" />
        </div>
        <div class="auth-field">
          <label for="email">Email</label>
          <input type="email" id="email" required autocomplete="email" />
        </div>
        <div class="auth-field">
          <label for="school">School (optional)</label>
          <input type="text" id="school" autocomplete="organization" />
        </div>
        <div class="auth-field">
          <label for="password">Password</label>
          <input type="password" id="password" required minlength="6" autocomplete="new-password" />
        </div>
        <button type="submit" class="auth-submit">Sign up</button>
        <div class="auth-error" id="error"></div>
      </form>
      <div class="auth-switch">
        Already have an account? <a href="login.html">Log in</a>
      </div>
    </div>
  </div>

  <script type="module">
    import { signup } from './js/auth.js';

    const form = document.getElementById('signup-form');
    const errorEl = document.getElementById('error');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.textContent = '';
      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const school = document.getElementById('school').value.trim();
      const password = document.getElementById('password').value;
      try {
        await signup({ email, password, name, school: school || null });
        location.href = 'dashboard.html';
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 4: Manual test**

Run: `cd frontend && python -m http.server 3000`, backend running on `localhost:8000`.
Open `http://localhost:3000/signup.html`, fill the form, submit.
Expected: redirects to `dashboard.html` (will 404/blank until Task 13 — that's expected at this point; confirm via devtools Network tab that the `POST /api/auth/signup` call returned 200 and `localStorage` now has `saathi-token`).

- [ ] **Step 5: Commit**

```bash
git add frontend/login.html frontend/signup.html frontend/css/auth.css
git commit -m "feat(auth): add login and signup pages"
```

---

## Task 13: Teacher dashboard

**Files:**
- Create: `frontend/dashboard.html`
- Create: `frontend/js/dashboard.js`
- Create: `frontend/css/dashboard.css`

**Interfaces:**
- Consumes: `frontend/js/auth.js` (`requireAuth`, `authFetch`, `getName`, `logout`), `GET /api/auth/me/history`.
- Produces: teacher's landing page after login — history list + resume + launch-classroom button.

- [ ] **Step 1: Write `frontend/css/dashboard.css`**

```css
/* dashboard.css · Teacher/admin dashboard shared layout */

.dash-page {
  min-height: 100vh;
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.dash-header h1 {
  font-family: 'Inter Tight', sans-serif;
  font-size: 1.4rem;
  margin: 0;
}

.dash-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.dash-btn {
  padding: 10px 18px;
  border-radius: 8px;
  border: 1px solid var(--border, rgba(255, 255, 255, 0.15));
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  text-decoration: none;
  font-size: 0.9rem;
}

.dash-btn.primary {
  background: var(--accent, #6ea8ff);
  color: #0a0a0f;
  border: none;
  font-weight: 600;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
}

.history-item .meta {
  font-size: 0.8rem;
  opacity: 0.7;
}

.history-empty {
  opacity: 0.6;
  padding: 40px 0;
  text-align: center;
}
```

- [ ] **Step 2: Write `frontend/js/dashboard.js`**

```javascript
/* dashboard.js · Teacher dashboard: history list + resume */

import { requireAuth, authFetch, getName, logout } from './auth.js';

if (requireAuth('teacher')) {
  init();
}

async function init() {
  document.getElementById('teacher-name').textContent = getName() || 'Teacher';
  document.getElementById('logout-btn').addEventListener('click', logout);

  const listEl = document.getElementById('history-list');
  try {
    const res = await authFetch('/api/auth/me/history');
    if (!res.ok) throw new Error('Failed to load history');
    const rows = await res.json();
    renderHistory(listEl, rows);
  } catch (err) {
    listEl.innerHTML = `<div class="history-empty">Couldn't load history: ${err.message}</div>`;
  }
}

function renderHistory(listEl, rows) {
  if (rows.length === 0) {
    listEl.innerHTML = '<div class="history-empty">No sessions yet — launch the classroom to get started.</div>';
    return;
  }
  listEl.innerHTML = '';
  for (const row of rows) {
    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
      <div>
        <div>${row.topic || row.intent}</div>
        <div class="meta">${row.intent} · Grade ${row.grade} · ${row.subject} · ${new Date(row.created_at).toLocaleString()}</div>
      </div>
      <button class="dash-btn resume-btn">Resume</button>
    `;
    item.querySelector('.resume-btn').addEventListener('click', () => resume(row));
    listEl.appendChild(item);
  }
}

function resume(row) {
  sessionStorage.setItem('saathi-resume', JSON.stringify(row));
  location.href = 'app.html';
}
```

- [ ] **Step 3: Write `frontend/dashboard.html`**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Saathi.AI · Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/main.css" />
  <link rel="stylesheet" href="css/dashboard.css" />
</head>
<body>
  <div class="dash-page">
    <div class="dash-header">
      <h1>Welcome, <span id="teacher-name">Teacher</span></h1>
      <div class="dash-actions">
        <a href="app.html" class="dash-btn primary">Launch classroom</a>
        <button id="logout-btn" class="dash-btn">Log out</button>
      </div>
    </div>
    <h2>Session history</h2>
    <div class="history-list" id="history-list">
      <div class="history-empty">Loading…</div>
    </div>
  </div>

  <script type="module" src="js/dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 4: Manual test**

Sign up (Task 12), confirm redirect lands on `dashboard.html` showing "Welcome, <name>" and "No sessions yet…". Log in as that user via `app.html` (once Task 15 wires its auth guard) — full loop tested at end of Task 15.

- [ ] **Step 5: Commit**

```bash
git add frontend/dashboard.html frontend/js/dashboard.js frontend/css/dashboard.css
git commit -m "feat(auth): add teacher dashboard with session history"
```

---

## Task 14: Admin dashboard

**Files:**
- Create: `frontend/admin.html`
- Create: `frontend/js/admin.js`

**Interfaces:**
- Consumes: `frontend/js/auth.js` (`requireAuth`, `authFetch`, `logout`), `GET/POST/PATCH /api/auth/admin/teachers`.
- Produces: admin's landing page — teacher list with active toggle + add-teacher form.

- [ ] **Step 1: Write `frontend/js/admin.js`**

```javascript
/* admin.js · Admin dashboard: teacher management */

import { requireAuth, authFetch, logout } from './auth.js';

if (requireAuth('admin')) {
  init();
}

async function init() {
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('add-teacher-form').addEventListener('submit', onAddTeacher);
  await loadTeachers();
}

async function loadTeachers() {
  const listEl = document.getElementById('teacher-list');
  const res = await authFetch('/api/auth/admin/teachers');
  if (!res.ok) {
    listEl.innerHTML = '<div class="history-empty">Failed to load teachers.</div>';
    return;
  }
  const teachers = await res.json();
  if (teachers.length === 0) {
    listEl.innerHTML = '<div class="history-empty">No teachers yet.</div>';
    return;
  }
  listEl.innerHTML = '';
  for (const t of teachers) {
    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
      <div>
        <div>${t.name} — ${t.email}</div>
        <div class="meta">${t.session_count} sessions · ${t.is_active ? 'active' : 'deactivated'}</div>
      </div>
      <button class="dash-btn toggle-btn">${t.is_active ? 'Deactivate' : 'Activate'}</button>
    `;
    item.querySelector('.toggle-btn').addEventListener('click', () => toggleTeacher(t.id, !t.is_active));
    listEl.appendChild(item);
  }
}

async function toggleTeacher(id, isActive) {
  await authFetch(`/api/auth/admin/teachers/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  });
  await loadTeachers();
}

async function onAddTeacher(e) {
  e.preventDefault();
  const errorEl = document.getElementById('add-error');
  errorEl.textContent = '';
  const name = document.getElementById('new-name').value.trim();
  const email = document.getElementById('new-email').value.trim();
  const password = document.getElementById('new-password').value;
  const res = await authFetch('/api/auth/admin/teachers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    errorEl.textContent = data.detail || 'Failed to add teacher';
    return;
  }
  e.target.reset();
  await loadTeachers();
}
```

- [ ] **Step 2: Write `frontend/admin.html`**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Saathi.AI · Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600&family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/main.css" />
  <link rel="stylesheet" href="css/dashboard.css" />
  <link rel="stylesheet" href="css/auth.css" />
</head>
<body>
  <div class="dash-page">
    <div class="dash-header">
      <h1>Admin</h1>
      <button id="logout-btn" class="dash-btn">Log out</button>
    </div>

    <h2>Add teacher</h2>
    <form id="add-teacher-form" class="auth-card" style="margin-bottom: 32px;">
      <div class="auth-field">
        <label for="new-name">Name</label>
        <input type="text" id="new-name" required />
      </div>
      <div class="auth-field">
        <label for="new-email">Email</label>
        <input type="email" id="new-email" required />
      </div>
      <div class="auth-field">
        <label for="new-password">Password</label>
        <input type="password" id="new-password" required minlength="6" />
      </div>
      <button type="submit" class="auth-submit">Add teacher</button>
      <div class="auth-error" id="add-error"></div>
    </form>

    <h2>Teachers</h2>
    <div class="history-list" id="teacher-list">
      <div class="history-empty">Loading…</div>
    </div>
  </div>

  <script type="module" src="js/admin.js"></script>
</body>
</html>
```

- [ ] **Step 3: Manual test**

Run `python -m scripts.create_admin` (Task 8) with test env vars, log in at `login.html` with those admin credentials, confirm redirect to `admin.html`, add a teacher via the form, confirm it appears in the list, click "Deactivate", confirm label flips and a subsequent login attempt with that teacher's credentials returns 403 (per Task 7's test).

- [ ] **Step 4: Commit**

```bash
git add frontend/admin.html frontend/js/admin.js
git commit -m "feat(auth): add admin dashboard for teacher management"
```

---

## Task 15: Guard app.html, resume-from-history, and landing page CTAs

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/index.html`

**Interfaces:**
- Consumes: `frontend/js/auth.js` (`requireAuth`).
- Produces: `app.html` redirects to `login.html` if no valid token is present; if `sessionStorage['saathi-resume']` is set (from Task 13's "Resume" button), the app pre-loads that history entry's content into the preview instead of starting fresh.

- [ ] **Step 1: Add the auth guard + resume hook to `frontend/js/app.js`**

At the top of `frontend/js/app.js`, add the import:
```javascript
import { requireAuth } from './auth.js';
```

Immediately after the existing imports, before the `// ── State ──` section, add:
```javascript
if (!requireAuth('teacher')) {
  throw new Error('redirecting to login');
}
```

This throw is deliberate: `requireAuth` has already triggered `location.href = 'login.html'` by this point, and throwing stops the rest of this module's top-level code (DOM wiring, session load) from running during the brief moment before the redirect navigates away.

Find where the module currently reads/creates the session on load (look for the existing call to `loadSession()` near the top-level init logic — not inside a function — in `frontend/js/app.js`). Immediately after that existing session-load logic, add:
```javascript
const resumeRaw = sessionStorage.getItem('saathi-resume');
if (resumeRaw) {
  sessionStorage.removeItem('saathi-resume');
  try {
    const resumeEntry = JSON.parse(resumeRaw);
    currentResponse = {
      intent: resumeEntry.intent,
      detected_language: resumeEntry.language,
      topic: resumeEntry.topic,
      grade: resumeEntry.grade,
      subject: resumeEntry.subject,
      content: resumeEntry.content_json,
    };
    renderPreview(currentResponse);
  } catch (e) {
    console.warn('Failed to resume history entry', e);
  }
}
```
(This uses the module's existing `currentResponse` state variable and `renderPreview` import, both already present at the top of `app.js`.)

- [ ] **Step 2: Update `frontend/index.html` CTAs**

In `frontend/index.html`, change the three existing links that currently point straight at `app.html`:
- Nav CTA (`<a href="app.html" class="nav-cta glass">Launch app</a>`) → `<a href="login.html" class="nav-cta glass">Log in</a>`
- Hero CTA (`<a href="app.html" class="btn-primary">Start teaching</a>`) → `<a href="signup.html" class="btn-primary">Start teaching</a>`

Leave the `display.html` projector links unchanged (per spec, display stays unauthenticated and reachable directly).

- [ ] **Step 3: Manual end-to-end test**

With backend running (`uvicorn main:app --reload` from `backend/`) and frontend served (`python -m http.server 3000` from `frontend/`):
1. Open `http://localhost:3000` → click "Start teaching" → lands on `signup.html`.
2. Sign up → redirects to `dashboard.html`, shows "No sessions yet".
3. Click "Launch classroom" → lands on `app.html` (no redirect back to login — token present).
4. Complete a session (pick grade/subject, type a transcript, process it).
5. Go back to `dashboard.html` (re-navigate manually) → the session now appears in history.
6. Click "Resume" on it → lands back on `app.html` with that content pre-rendered in the preview pane.
7. Open `http://localhost:3000/app.html` in a fresh incognito window (no token) → confirm it redirects to `login.html`.

Expected: all 7 steps behave as described.

- [ ] **Step 4: Commit**

```bash
git add frontend/js/app.js frontend/index.html
git commit -m "feat(auth): guard app.html behind login, wire history resume, update landing CTAs"
```

---

## What you still need to do (not automatable by this plan)

- Provision an actual Postgres instance (Render Postgres, Neon, or Supabase — your call from the earlier design discussion) and set `DATABASE_URL` in the Render dashboard.
- Set `JWT_SECRET` (a long random string), `ADMIN_EMAIL`, `ADMIN_PASSWORD` in the Render dashboard as secrets.
- After the first deploy with the new `render.yaml`, run `python -m scripts.create_admin` once against production (e.g. via Render's shell) to seed the real admin account.
- Rotate `ADMIN_PASSWORD` after first login if you want it out of the Render env history.
