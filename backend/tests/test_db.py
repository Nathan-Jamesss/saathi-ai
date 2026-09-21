from sqlalchemy import text
from sqlmodel import Session
from db import engine


def test_engine_connects():
    with Session(engine) as session:
        result = session.exec(text("SELECT 1")).one()
        assert result == (1,) or result == 1
