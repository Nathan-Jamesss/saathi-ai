import csv
import io
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from sqlmodel import Session

from auth.models import Role, User
from auth.security import create_token, hash_password
from db import engine


def _admin_token(email):
    with Session(engine) as db:
        admin = User(email=email, password_hash=hash_password("pw"), role=Role.admin, name="Admin")
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return create_token(admin.id, "admin")


def _teacher(client, email, name):
    signup = client.post(
        "/api/auth/signup", json={"email": email, "password": "oldpw", "name": name}
    )
    return {"Authorization": f"Bearer {signup.json()['token']}"}


def _schedule(client, headers, days_offsets):
    """Give a teacher one class on each of today+offset (offsets can be negative)."""
    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 9, "subject": "science", "content": "Ch1"},
        headers=headers,
    )
    start = date.today() + timedelta(days=min(days_offsets))
    end = date.today() + timedelta(days=max(days_offsets))
    sessions = [{"chapter": f"Ch{i}", "focus": "f"} for i in range((end - start).days + 1)]
    with patch("auth.routes.generate_schedule", new=AsyncMock(return_value=sessions)):
        client.post(
            "/api/auth/me/schedule/generate",
            json={
                "grade": 9,
                "subject": "science",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "classes_per_week": 7,
            },
            headers=headers,
        )


# ── progress ──

def test_progress_requires_admin(client):
    headers = _teacher(client, "ins-nonadmin@example.com", "T")
    assert client.get("/api/auth/admin/progress", headers=headers).status_code == 403


def test_progress_reports_done_and_remaining_per_teacher(client):
    admin = _admin_token("ins-admin-progress@example.com")
    headers = _teacher(client, "ins-progress@example.com", "Progress Teacher")
    # 3 days ago .. 2 days ahead = 6 classes; 3 are in the past, 3 today-or-later
    _schedule(client, headers, [-3, 2])

    rows = client.get(
        "/api/auth/admin/progress", headers={"Authorization": f"Bearer {admin}"}
    ).json()
    mine = next(r for r in rows if r["teacher_name"] == "Progress Teacher")

    assert mine["total_classes"] == 6
    assert mine["done_classes"] == 3
    assert mine["percent_done"] == 50


def test_progress_handles_teacher_with_no_schedule(client):
    admin = _admin_token("ins-admin-empty@example.com")
    _teacher(client, "ins-noschedule@example.com", "No Schedule Teacher")

    rows = client.get(
        "/api/auth/admin/progress", headers={"Authorization": f"Bearer {admin}"}
    ).json()
    mine = next(r for r in rows if r["teacher_name"] == "No Schedule Teacher")
    assert mine["total_classes"] == 0
    assert mine["percent_done"] == 0


# ── activity ──

def test_activity_requires_admin(client):
    headers = _teacher(client, "ins-act-nonadmin@example.com", "T")
    assert client.get("/api/auth/admin/activity", headers=headers).status_code == 403


def test_activity_returns_one_entry_per_day(client):
    admin = _admin_token("ins-admin-activity@example.com")
    resp = client.get(
        "/api/auth/admin/activity?days=14", headers={"Authorization": f"Bearer {admin}"}
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 14
    assert rows[-1]["date"] == date.today().isoformat()
    assert all("sessions" in r for r in rows)


def test_activity_counts_todays_sessions(client):
    admin = _admin_token("ins-admin-activity2@example.com")
    headers = _teacher(client, "ins-activity@example.com", "Active Teacher")

    with patch(
        "api.process.route_intent",
        new=AsyncMock(return_value={
            "intent": "concept_simplification", "topic": "x", "grade": 9,
            "subject": "science", "language": "en", "confidence": 0.9,
        }),
    ), patch("api.process.generate_concept", new=AsyncMock(return_value={"explanation": "x"})):
        client.post(
            "/api/process",
            json={"transcript": "explain x", "session": {}, "regenerate": False},
            headers=headers,
        )

    rows = client.get(
        "/api/auth/admin/activity?days=7", headers={"Authorization": f"Bearer {admin}"}
    ).json()
    assert rows[-1]["sessions"] >= 1


# ── password reset ──

def test_admin_can_reset_teacher_password(client):
    admin = _admin_token("ins-admin-reset@example.com")
    headers = _teacher(client, "ins-reset@example.com", "Reset Me")
    teacher_id = client.get("/api/auth/me", headers=headers).json()["id"]

    resp = client.patch(
        f"/api/auth/admin/teachers/{teacher_id}/password",
        json={"password": "brand-new-pw"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 200

    old = client.post(
        "/api/auth/login", json={"email": "ins-reset@example.com", "password": "oldpw"}
    )
    new = client.post(
        "/api/auth/login", json={"email": "ins-reset@example.com", "password": "brand-new-pw"}
    )
    assert old.status_code == 401
    assert new.status_code == 200


def test_password_reset_rejects_short_password(client):
    admin = _admin_token("ins-admin-short@example.com")
    headers = _teacher(client, "ins-short@example.com", "Short")
    teacher_id = client.get("/api/auth/me", headers=headers).json()["id"]

    resp = client.patch(
        f"/api/auth/admin/teachers/{teacher_id}/password",
        json={"password": "123"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 400


def test_password_reset_requires_admin(client):
    headers = _teacher(client, "ins-reset-nonadmin@example.com", "T")
    resp = client.patch(
        "/api/auth/admin/teachers/1/password", json={"password": "whatever123"}, headers=headers
    )
    assert resp.status_code == 403


def test_password_reset_unknown_teacher_404(client):
    admin = _admin_token("ins-admin-404@example.com")
    resp = client.patch(
        "/api/auth/admin/teachers/999999/password",
        json={"password": "whatever123"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 404


# ── CSV report ──

def test_report_requires_admin(client):
    headers = _teacher(client, "ins-report-nonadmin@example.com", "T")
    assert client.get("/api/auth/admin/report.csv", headers=headers).status_code == 403


def test_report_is_a_csv_with_a_row_per_teacher(client):
    admin = _admin_token("ins-admin-report@example.com")
    headers = _teacher(client, "ins-report@example.com", "Report Teacher")
    _schedule(client, headers, [-1, 1])

    resp = client.get(
        "/api/auth/admin/report.csv", headers={"Authorization": f"Bearer {admin}"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(resp.text)))
    mine = next(r for r in rows if r["Teacher"] == "Report Teacher")
    assert mine["Email"] == "ins-report@example.com"
    assert mine["Total classes"] == "3"
    assert mine["Classes done"] == "1"
