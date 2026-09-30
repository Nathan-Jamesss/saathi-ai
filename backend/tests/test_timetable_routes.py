from datetime import date
from unittest.mock import patch

from core.schedule import compute_class_dates


def _signup_token(client, email):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "pw123", "name": "TT"},
    )
    return resp.json()["token"]


# ── compute_class_dates with explicit weekdays ──

def test_compute_class_dates_uses_explicit_weekdays():
    # 2026-01-05 is a Monday. Tue(1)/Thu(3) only, over two weeks.
    dates = compute_class_dates(date(2026, 1, 5), date(2026, 1, 18), 3, weekdays=[1, 3])
    assert all(d.weekday() in {1, 3} for d in dates)
    assert len(dates) == 4


def test_compute_class_dates_falls_back_when_no_weekdays():
    dates = compute_class_dates(date(2026, 1, 5), date(2026, 1, 18), 2, weekdays=None)
    assert len(dates) == 4  # 2 per week over 2 weeks


# ── timetable upload ──

def test_timetable_upload_requires_token(client):
    resp = client.post(
        "/api/auth/me/timetable/upload",
        data={"grade": "9", "subject": "science"},
        files={"file": ("tt.pdf", b"%PDF-fake", "application/pdf")},
    )
    assert resp.status_code == 401


def test_timetable_upload_extracts_and_saves(client):
    token = _signup_token(client, "tt-upload@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "auth.routes.extract_timetable",
        return_value={"weekdays": [1, 3], "note": "Science: Tue & Thu, period 2"},
    ):
        resp = client.post(
            "/api/auth/me/timetable/upload",
            data={"grade": "9", "subject": "science"},
            files={"file": ("tt.pdf", b"%PDF-fake", "application/pdf")},
            headers=headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["weekdays"] == [1, 3]
    assert "Tue" in body["note"]

    get_resp = client.get(
        "/api/auth/me/timetable",
        params={"grade": 9, "subject": "science"},
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["weekdays"] == [1, 3]


def test_timetable_get_empty_when_none_saved(client):
    token = _signup_token(client, "tt-empty@example.com")
    resp = client.get(
        "/api/auth/me/timetable",
        params={"grade": 10, "subject": "science"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["weekdays"] == []


def test_timetable_upload_overwrites_previous(client):
    token = _signup_token(client, "tt-overwrite@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    for weekdays in ([0, 2], [4]):
        with patch(
            "auth.routes.extract_timetable",
            return_value={"weekdays": weekdays, "note": "x"},
        ):
            client.post(
                "/api/auth/me/timetable/upload",
                data={"grade": "9", "subject": "science"},
                files={"file": ("tt.pdf", b"%PDF-fake", "application/pdf")},
                headers=headers,
            )

    resp = client.get(
        "/api/auth/me/timetable",
        params={"grade": 9, "subject": "science"},
        headers=headers,
    )
    assert resp.json()["weekdays"] == [4]


# ── schedule generation honours the uploaded timetable ──

def test_schedule_generate_uses_uploaded_timetable_days(client):
    from unittest.mock import AsyncMock

    token = _signup_token(client, "tt-schedule@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 9, "subject": "science", "content": "Ch1\nCh2"},
        headers=headers,
    )

    with patch(
        "auth.routes.extract_timetable",
        return_value={"weekdays": [1, 3], "note": "Tue/Thu"},
    ):
        client.post(
            "/api/auth/me/timetable/upload",
            data={"grade": "9", "subject": "science"},
            files={"file": ("tt.pdf", b"%PDF-fake", "application/pdf")},
            headers=headers,
        )

    fake_sessions = [{"chapter": "Ch1", "focus": "a"}] * 10
    with patch("auth.routes.generate_schedule", new=AsyncMock(return_value=fake_sessions)):
        resp = client.post(
            "/api/auth/me/schedule/generate",
            json={
                "grade": 9,
                "subject": "science",
                "start_date": "2026-01-05",
                "end_date": "2026-01-18",
                "classes_per_week": 5,  # should be ignored in favour of the uploaded Tue/Thu
            },
            headers=headers,
        )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 4  # Tue + Thu over two weeks, not 5/week
    for row in rows:
        assert date.fromisoformat(row["scheduled_date"]).weekday() in {1, 3}
