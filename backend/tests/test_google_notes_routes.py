import os
from unittest.mock import patch

import pytest

from core import google_oauth


def _signup_token(client, email):
    resp = client.post(
        "/api/auth/signup", json={"email": email, "password": "pw123", "name": "N"}
    )
    return resp.json()["token"]


@pytest.fixture()
def google_configured():
    """Pretend the Google OAuth env vars are set."""
    with patch.dict(
        os.environ,
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/auth/google/callback",
        },
    ):
        yield


# ── connection status ──

def test_google_status_reports_not_configured(client):
    token = _signup_token(client, "g-notconf@example.com")
    with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        resp = client.get(
            "/api/auth/me/google", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    assert resp.json()["configured"] is False
    assert resp.json()["connected"] is False


def test_google_status_not_connected_when_configured(client, google_configured):
    token = _signup_token(client, "g-notconnected@example.com")
    resp = client.get("/api/auth/me/google", headers={"Authorization": f"Bearer {token}"})
    assert resp.json() == {"configured": True, "connected": False, "google_email": ""}


def test_authorize_url_requires_configuration(client):
    token = _signup_token(client, "g-authnoconf@example.com")
    with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        resp = client.get(
            "/api/auth/google/authorize", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 503


def test_authorize_url_built_for_user(client, google_configured):
    token = _signup_token(client, "g-auth@example.com")
    resp = client.get(
        "/api/auth/google/authorize", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "test-client-id" in url
    assert "documents" in url


# ── callback stores the connection ──

def test_callback_stores_tokens_and_connects(client, google_configured):
    token = _signup_token(client, "g-callback@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    state = google_oauth.make_state(user_id)

    with patch(
        "auth.routes.exchange_code",
        return_value={"refresh_token": "rt-123", "access_token": "at-123", "expires_in": 3600},
    ), patch("auth.routes.fetch_google_email", return_value="teacher@gmail.com"):
        resp = client.get(
            f"/api/auth/google/callback?code=fake-code&state={state}",
            follow_redirects=False,
        )
    assert resp.status_code in (302, 307)

    status = client.get("/api/auth/me/google", headers=headers).json()
    assert status["connected"] is True
    assert status["google_email"] == "teacher@gmail.com"


# ── notes doc ──

def test_notes_requires_google_connection(client, google_configured):
    token = _signup_token(client, "g-nonotes@example.com")
    resp = client.post(
        "/api/auth/me/notes",
        json={"grade": 9, "subject": "science"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def _connect_google(client, headers):
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    state = google_oauth.make_state(user_id)
    with patch(
        "auth.routes.exchange_code",
        return_value={"refresh_token": "rt", "access_token": "at", "expires_in": 3600},
    ), patch("auth.routes.fetch_google_email", return_value="t@gmail.com"):
        client.get(f"/api/auth/google/callback?code=c&state={state}", follow_redirects=False)


def test_create_notes_doc_and_reuse_it(client, google_configured):
    token = _signup_token(client, "g-notes@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _connect_google(client, headers)

    with patch(
        "auth.routes.create_doc",
        return_value={"doc_id": "doc-1", "doc_url": "https://docs.google.com/document/d/doc-1/edit"},
    ) as mock_create:
        first = client.post(
            "/api/auth/me/notes", json={"grade": 9, "subject": "science"}, headers=headers
        )
        second = client.post(
            "/api/auth/me/notes", json={"grade": 9, "subject": "science"}, headers=headers
        )

    assert first.status_code == 200
    assert first.json()["doc_url"].endswith("/doc-1/edit")
    # Second call reuses the existing doc rather than creating another.
    assert mock_create.call_count == 1
    assert second.json()["doc_id"] == "doc-1"


def test_get_notes_returns_empty_when_none(client, google_configured):
    token = _signup_token(client, "g-notes-empty@example.com")
    resp = client.get(
        "/api/auth/me/notes",
        params={"grade": 9, "subject": "science"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["doc_url"] == ""


def test_append_note_to_doc(client, google_configured):
    token = _signup_token(client, "g-append@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _connect_google(client, headers)

    with patch(
        "auth.routes.create_doc",
        return_value={"doc_id": "doc-2", "doc_url": "https://docs.google.com/document/d/doc-2/edit"},
    ):
        client.post("/api/auth/me/notes", json={"grade": 9, "subject": "science"}, headers=headers)

    with patch("auth.routes.append_text") as mock_append:
        resp = client.post(
            "/api/auth/me/notes/append",
            json={"grade": 9, "subject": "science", "text": "Remember: revise Ch 2 before the test"},
            headers=headers,
        )
    assert resp.status_code == 200
    mock_append.assert_called_once()
    assert "revise Ch 2" in mock_append.call_args[0][2]


def test_disconnect_google(client, google_configured):
    token = _signup_token(client, "g-disconnect@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _connect_google(client, headers)
    assert client.get("/api/auth/me/google", headers=headers).json()["connected"] is True

    resp = client.delete("/api/auth/me/google", headers=headers)
    assert resp.status_code == 200
    assert client.get("/api/auth/me/google", headers=headers).json()["connected"] is False


def test_list_all_notes_docs_returns_every_class_doc(client, google_configured):
    token = _signup_token(client, "g-listnotes@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _connect_google(client, headers)

    assert client.get("/api/auth/me/notes/all", headers=headers).json() == []

    for grade, subject in [(10, "science"), (9, "history")]:
        with patch(
            "auth.routes.create_doc",
            return_value={"doc_id": f"d-{grade}", "doc_url": f"https://docs.google.com/document/d/d-{grade}/edit"},
        ):
            client.post("/api/auth/me/notes", json={"grade": grade, "subject": subject}, headers=headers)

    rows = client.get("/api/auth/me/notes/all", headers=headers).json()
    assert [(r["grade"], r["subject"]) for r in rows] == [(9, "history"), (10, "science")]
    assert rows[0]["doc_url"].endswith("/d-9/edit")
