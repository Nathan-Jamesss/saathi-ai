from sqlalchemy import create_engine, inspect, text


def test_ensure_added_columns_adds_missing_column(monkeypatch):
    import db
    eng = create_engine("sqlite://")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE scheduledclass (id INTEGER PRIMARY KEY, chapter VARCHAR)"))
        c.execute(text("INSERT INTO scheduledclass (id, chapter) VALUES (1, 'x')"))
    monkeypatch.setattr(db, "engine", eng)
    db.ensure_added_columns()
    db.ensure_added_columns()  # idempotent
    assert "calendar_event_id" in {c["name"] for c in inspect(eng).get_columns("scheduledclass")}
    with eng.connect() as c:
        assert c.execute(text("SELECT calendar_event_id FROM scheduledclass")).scalar() == ""
