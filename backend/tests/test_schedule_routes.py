from datetime import date
from unittest.mock import AsyncMock, patch

from core.schedule import compute_class_dates


def _signup_token(client, email="schedule-teacher@example.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "pw123", "name": "S"},
    )
    return resp.json()["token"]


def _save_syllabus(client, headers, grade=10, subject="science", content="Ch1\nCh2\nCh3"):
    client.put(
        "/api/auth/me/syllabus",
        json={"grade": grade, "subject": subject, "content": content},
        headers=headers,
    )


# ── compute_class_dates (pure function) ──

def test_compute_class_dates_three_per_week():
    dates = compute_class_dates(date(2026, 1, 5), date(2026, 1, 18), 3)  # 2 full weeks, Mon 2026-01-05
    assert all(d.weekday() in {0, 2, 4} for d in dates)
    assert len(dates) == 6


def test_compute_class_dates_one_per_week():
    dates = compute_class_dates(date(2026, 1, 5), date(2026, 1, 18), 1)
    assert len(dates) == 2


# ── syllabus PDF upload ──

def test_upload_syllabus_pdf_requires_token(client):
    resp = client.post(
        "/api/auth/me/syllabus/upload",
        data={"grade": "10", "subject": "science"},
        files={"file": ("syllabus.pdf", b"%PDF-fake", "application/pdf")},
    )
    assert resp.status_code == 401


def test_upload_syllabus_pdf_extracts_and_saves(client):
    token = _signup_token(client, "pdf-upload@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "auth.routes.extract_syllabus_from_pdf",
        return_value="Chapter 1: Matter\nChapter 2: Motion",
    ):
        resp = client.post(
            "/api/auth/me/syllabus/upload",
            data={"grade": "9", "subject": "science"},
            files={"file": ("syllabus.pdf", b"%PDF-fake", "application/pdf")},
            headers=headers,
        )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Chapter 1: Matter\nChapter 2: Motion"

    get_resp = client.get(
        "/api/auth/me/syllabus",
        params={"grade": 9, "subject": "science"},
        headers=headers,
    )
    assert get_resp.json()["content"] == "Chapter 1: Matter\nChapter 2: Motion"


# ── schedule generation ──

def test_generate_schedule_requires_saved_syllabus(client):
    token = _signup_token(client, "no-syllabus@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/auth/me/schedule/generate",
        json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-18", "classes_per_week": 3},
        headers=headers,
    )
    assert resp.status_code == 400


def test_generate_schedule_creates_scheduled_classes(client):
    token = _signup_token(client, "gen-schedule@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _save_syllabus(client, headers)

    fake_sessions = [
        {"chapter": "Ch1", "focus": "intro"},
        {"chapter": "Ch1", "focus": "part 2"},
        {"chapter": "Ch2", "focus": "intro"},
        {"chapter": "Ch2", "focus": "part 2"},
        {"chapter": "Ch3", "focus": "intro"},
        {"chapter": "Ch3", "focus": "wrap up"},
    ]
    with patch("auth.routes.generate_schedule", new=AsyncMock(return_value=fake_sessions)):
        resp = client.post(
            "/api/auth/me/schedule/generate",
            json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-18", "classes_per_week": 3},
            headers=headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 6
    assert body[0]["class_number"] == 1
    assert body[0]["scheduled_date"] == "2026-01-05"
    assert body[-1]["scheduled_date"] == "2026-01-16"


def test_generate_schedule_replaces_previous_schedule(client):
    token = _signup_token(client, "regen-schedule@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _save_syllabus(client, headers)

    with patch(
        "auth.routes.generate_schedule",
        new=AsyncMock(return_value=[{"chapter": "Ch1", "focus": "a"}]),
    ):
        client.post(
            "/api/auth/me/schedule/generate",
            json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-05", "classes_per_week": 1},
            headers=headers,
        )
        resp = client.post(
            "/api/auth/me/schedule/generate",
            json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-05", "classes_per_week": 1},
            headers=headers,
        )
    assert len(resp.json()) == 1

    list_resp = client.get(
        "/api/auth/me/schedule", params={"grade": 10, "subject": "science"}, headers=headers
    )
    assert len(list_resp.json()) == 1


def test_list_schedule_sorted_by_date(client):
    token = _signup_token(client, "list-schedule@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _save_syllabus(client, headers)

    with patch(
        "auth.routes.generate_schedule",
        new=AsyncMock(return_value=[{"chapter": "Ch1", "focus": "a"}, {"chapter": "Ch2", "focus": "b"}]),
    ):
        client.post(
            "/api/auth/me/schedule/generate",
            json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-08", "classes_per_week": 1},
            headers=headers,
        )

    resp = client.get(
        "/api/auth/me/schedule", params={"grade": 10, "subject": "science"}, headers=headers
    )
    dates = [row["scheduled_date"] for row in resp.json()]
    assert dates == sorted(dates)


def test_delete_scheduled_class(client):
    token = _signup_token(client, "delete-schedule@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _save_syllabus(client, headers)

    with patch(
        "auth.routes.generate_schedule",
        new=AsyncMock(return_value=[{"chapter": "Ch1", "focus": "a"}]),
    ):
        gen_resp = client.post(
            "/api/auth/me/schedule/generate",
            json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-05", "classes_per_week": 1},
            headers=headers,
        )
    entry_id = gen_resp.json()[0]["id"]

    del_resp = client.delete(f"/api/auth/me/schedule/{entry_id}", headers=headers)
    assert del_resp.status_code == 200

    list_resp = client.get(
        "/api/auth/me/schedule", params={"grade": 10, "subject": "science"}, headers=headers
    )
    assert list_resp.json() == []


def test_delete_scheduled_class_requires_ownership(client):
    token1 = _signup_token(client, "owner1@example.com")
    token2 = _signup_token(client, "owner2@example.com")
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    _save_syllabus(client, headers1)

    with patch(
        "auth.routes.generate_schedule",
        new=AsyncMock(return_value=[{"chapter": "Ch1", "focus": "a"}]),
    ):
        gen_resp = client.post(
            "/api/auth/me/schedule/generate",
            json={"grade": 10, "subject": "science", "start_date": "2026-01-05", "end_date": "2026-01-05", "classes_per_week": 1},
            headers=headers1,
        )
    entry_id = gen_resp.json()[0]["id"]

    resp = client.delete(f"/api/auth/me/schedule/{entry_id}", headers=headers2)
    assert resp.status_code == 404
