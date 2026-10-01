import os
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from core import google_oauth


@pytest.fixture()
def google_configured():
    with patch.dict(
        os.environ,
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/auth/google/callback",
        },
    ):
        yield


def _teacher_with_schedule(client, email, how_many=2):
    signup = client.post(
        "/api/auth/signup", json={"email": email, "password": "pw", "name": "Cal Teacher"}
    )
    headers = {"Authorization": f"Bearer {signup.json()['token']}"}
    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 9, "subject": "science", "content": "Ch1\nCh2"},
        headers=headers,
    )
    start = date.today() + timedelta(days=1)
    sessions = [{"chapter": f"Ch{i}", "focus": "f"} for i in range(how_many)]
    with patch("auth.routes.generate_schedule", new=AsyncMock(return_value=sessions)):
        client.post(
            "/api/auth/me/schedule/generate",
            json={
                "grade": 9,
                "subject": "science",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=how_many - 1)).isoformat(),
                "classes_per_week": 7,
            },
            headers=headers,
        )
    return headers


def _connect_google(client, headers):
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    state = google_oauth.make_state(user_id)
    with patch(
        "auth.routes.exchange_code",
        return_value={"refresh_token": "rt", "access_token": "at", "expires_in": 3600},
    ), patch("auth.routes.fetch_google_email", return_value="t@gmail.com"):
        client.get(f"/api/auth/google/callback?code=c&state={state}", follow_redirects=False)


def test_calendar_sync_requires_google_connection(client, google_configured):
    headers = _teacher_with_schedule(client, "cal-noconn@example.com")
    resp = client.post(
        "/api/auth/me/schedule/sync-calendar",
        json={"grade": 9, "subject": "science"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_calendar_sync_creates_one_event_per_class(client, google_configured):
    headers = _teacher_with_schedule(client, "cal-sync@example.com", how_many=2)
    _connect_google(client, headers)

    with patch("auth.routes.upsert_class_event", side_effect=["ev-1", "ev-2"]) as mock_upsert:
        resp = client.post(
            "/api/auth/me/schedule/sync-calendar",
            json={"grade": 9, "subject": "science"},
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.json()["synced"] == 2
    assert mock_upsert.call_count == 2


def test_calendar_resync_updates_instead_of_duplicating(client, google_configured):
    headers = _teacher_with_schedule(client, "cal-resync@example.com", how_many=2)
    _connect_google(client, headers)

    with patch("auth.routes.upsert_class_event", side_effect=["ev-1", "ev-2"]):
        client.post(
            "/api/auth/me/schedule/sync-calendar",
            json={"grade": 9, "subject": "science"},
            headers=headers,
        )

    # Second sync should pass the stored event ids back in, not create new ones.
    with patch("auth.routes.upsert_class_event", side_effect=["ev-1", "ev-2"]) as mock_upsert:
        resp = client.post(
            "/api/auth/me/schedule/sync-calendar",
            json={"grade": 9, "subject": "science"},
            headers=headers,
        )

    assert resp.json()["synced"] == 2
    passed_event_ids = [call.args[1] for call in mock_upsert.call_args_list]
    assert set(passed_event_ids) == {"ev-1", "ev-2"}


def test_calendar_sync_sends_chapter_and_class_details(client, google_configured):
    headers = _teacher_with_schedule(client, "cal-details@example.com", how_many=1)
    _connect_google(client, headers)

    with patch("auth.routes.upsert_class_event", return_value="ev-9") as mock_upsert:
        client.post(
            "/api/auth/me/schedule/sync-calendar",
            json={"grade": 9, "subject": "science"},
            headers=headers,
        )

    summary = mock_upsert.call_args.args[2]
    assert "Ch0" in summary
    assert "Class 9" in summary
