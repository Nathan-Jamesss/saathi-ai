"""Shared test fixtures — spins up the Firestore emulator for the whole
test session (via `firebase emulators:start`) and clears its data between
tests so tests stay isolated, same guarantee the old per-session SQLite
tempfile gave us."""
import os
import subprocess
import time

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

EMULATOR_HOST = "localhost:8080"
EMULATOR_PROJECT = "demo-test"
os.environ["FIRESTORE_EMULATOR_HOST"] = EMULATOR_HOST
os.environ["GOOGLE_CLOUD_PROJECT"] = EMULATOR_PROJECT

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

from fastapi.testclient import TestClient  # noqa: E402
import main as main_module  # noqa: E402


def _emulator_ready() -> bool:
    try:
        return httpx.get(f"http://{EMULATOR_HOST}/", timeout=1).status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def _firestore_emulator():
    if _emulator_ready():
        # Already running (e.g. started manually in another terminal) — reuse it.
        yield
        return

    proc = subprocess.Popen(
        [
            "firebase", "emulators:start", "--only", "firestore",
            "--project", EMULATOR_PROJECT,
        ],
        cwd=_REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )
    for _ in range(60):
        if _emulator_ready():
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(
            "Firestore emulator didn't come up in 30s. "
            "Run `firebase emulators:start --only firestore` yourself and re-run pytest."
        )

    yield

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(autouse=True)
def _clear_firestore():
    yield
    httpx.delete(
        f"http://{EMULATOR_HOST}/emulator/v1/projects/{EMULATOR_PROJECT}/databases/(default)/documents",
        timeout=5,
    )


@pytest.fixture()
def client():
    return TestClient(main_module.app)
