from unittest.mock import AsyncMock, patch

from sqlmodel import Session


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


def test_process_history_save_failure_does_not_fail_request(client):
    token = _signup(client, "hist3@example.com")

    with patch(
        "api.process.route_intent",
        new=AsyncMock(
            return_value={
                "intent": "concept_simplification",
                "topic": "osmosis",
                "grade": 10,
                "subject": "science",
                "language": "en",
                "confidence": 0.9,
            }
        ),
    ), patch(
        "api.process.generate_concept",
        new=AsyncMock(return_value={"explanation": "water moves across membranes"}),
    ), patch.object(
        Session, "commit", side_effect=Exception("db unavailable")
    ):
        resp = client.post(
            "/api/process",
            json={"transcript": "explain osmosis", "session": {}, "regenerate": False},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "concept_simplification"
    assert body["topic"] == "osmosis"
    assert body["content"]["explanation"] == "water moves across membranes"


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
