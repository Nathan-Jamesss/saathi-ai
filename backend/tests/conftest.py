"""Shared test fixtures — an isolated SQLite DB per test session."""
import os
import tempfile

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from db import engine  # noqa: E402
import main as main_module  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    from auth import models  # noqa: F401  (ensures tables are registered)
    SQLModel.metadata.create_all(engine)
    yield
    engine.dispose()
    os.close(_db_fd)
    os.remove(_db_path)


@pytest.fixture()
def client():
    return TestClient(main_module.app)
