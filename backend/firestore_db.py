"""Firestore client — the Google-native replacement for db.py (SQLModel/Postgres).

Local dev: set FIRESTORE_EMULATOR_HOST=localhost:8080 (run via
`firebase emulators:start --only firestore`) and the client talks to the
emulator with no real credentials needed.

Production: set GOOGLE_CLOUD_PROJECT and rely on Application Default
Credentials (a service account attached to the Cloud Run service, or
`gcloud auth application-default login` locally).
"""
import os
from functools import lru_cache

from google.cloud import firestore


@lru_cache
def get_client() -> firestore.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("FIRESTORE_PROJECT_ID")
    return firestore.Client(project=project) if project else firestore.Client()
