"""Google OAuth — lets a teacher connect their own Google account so Saathi
can write notes into their Drive as real Google Docs.

Needs three env vars, set once in the Cloud Run / Render dashboard:
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
Until those are set, is_configured() is False and the feature stays off
instead of erroring.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

# documents = create/edit Docs. drive.file = only the files we create, never
# the teacher's whole Drive.
SCOPES = "https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive.file"

STATE_TTL_SECONDS = 600


def is_configured() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def _client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "")


def _client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")


def _redirect_uri() -> str:
    return os.environ.get("GOOGLE_REDIRECT_URI", "")


def _state_secret() -> str:
    return os.environ.get("JWT_SECRET", "dev-secret-change-me")


def make_state(user_id: int) -> str:
    return jwt.encode(
        {"sub": str(user_id), "exp": int(time.time()) + STATE_TTL_SECONDS},
        _state_secret(),
        algorithm="HS256",
    )


def read_state(state: str) -> int:
    payload = jwt.decode(state, _state_secret(), algorithms=["HS256"])
    return int(payload["sub"])


def build_authorize_url(user_id: int) -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",      # so we get a refresh token
        "prompt": "consent",           # so we reliably get one on reconnect
        "include_granted_scopes": "true",
        "state": make_state(user_id),
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Trade the one-time code from Google's redirect for tokens."""
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "refresh_token": refresh_token,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_google_email(access_token: str) -> str:
    try:
        resp = httpx.get(
            USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("email", "")
    except Exception:
        return ""


def expiry_from_now(expires_in: Optional[int]) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in or 3600))
