"""Database engine & session dependency"""
import os
from sqlalchemy import inspect, text
from sqlmodel import create_engine, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/saathi.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


def get_db():
    with Session(engine) as session:
        yield session


# Columns added after a table first went live. create_all() makes missing
# tables but never alters existing ones, so add these here when absent.
_ADDED_COLUMNS = [
    ("scheduledclass", "calendar_event_id", "VARCHAR NOT NULL DEFAULT ''"),
]


def ensure_added_columns():
    insp = inspect(engine)
    for table, column, ddl in _ADDED_COLUMNS:
        if not insp.has_table(table):
            continue
        if column in {c["name"] for c in insp.get_columns(table)}:
            continue
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
