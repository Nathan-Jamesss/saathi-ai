def _signup_token(client, email="syllabus-teacher@example.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "pw123", "name": "S"},
    )
    return resp.json()["token"]


def test_get_syllabus_empty_when_none_saved(client):
    token = _signup_token(client)
    resp = client.get(
        "/api/auth/me/syllabus",
        params={"grade": 9, "subject": "science"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"grade": 9, "subject": "science", "content": ""}


def test_save_then_get_syllabus_roundtrip(client):
    token = _signup_token(client, "syllabus-roundtrip@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    put_resp = client.put(
        "/api/auth/me/syllabus",
        json={"grade": 9, "subject": "science", "content": "Ch1: Matter\nCh2: Motion"},
        headers=headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["content"] == "Ch1: Matter\nCh2: Motion"

    get_resp = client.get(
        "/api/auth/me/syllabus",
        params={"grade": 9, "subject": "science"},
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == "Ch1: Matter\nCh2: Motion"


def test_save_syllabus_upserts_not_duplicates(client):
    token = _signup_token(client, "syllabus-upsert@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 10, "subject": "math", "content": "first draft"},
        headers=headers,
    )
    resp = client.put(
        "/api/auth/me/syllabus",
        json={"grade": 10, "subject": "math", "content": "final draft"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "final draft"


def test_syllabus_scoped_per_grade_and_subject(client):
    token = _signup_token(client, "syllabus-scoped@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/auth/me/syllabus",
        json={"grade": 6, "subject": "science", "content": "grade 6 content"},
        headers=headers,
    )
    resp = client.get(
        "/api/auth/me/syllabus",
        params={"grade": 7, "subject": "science"},
        headers=headers,
    )
    assert resp.json()["content"] == ""


def test_syllabus_requires_token(client):
    resp = client.get("/api/auth/me/syllabus", params={"grade": 9, "subject": "science"})
    assert resp.status_code == 401
