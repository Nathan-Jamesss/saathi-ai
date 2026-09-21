"""Database engine & session dependency"""
import os
from sqlmodel import create_engine, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/saathi.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


def get_db():
    with Session(engine) as session:
        yield session
