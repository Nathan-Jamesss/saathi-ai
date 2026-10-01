import asyncio
from datetime import date
from unittest.mock import patch

from core.schedule import generate_schedule


def test_generate_schedule_falls_back_when_ai_unavailable():
    dates = [date(2026, 10, d) for d in (9, 12, 14, 16)]
    syllabus = "Chapter 1: Chemical Reactions\nChapter 2: Acids, Bases and Salts"
    with patch("core.schedule.generate_content", side_effect=Exception("429 RESOURCE_EXHAUSTED")), \
         patch("asyncio.sleep", new=lambda *_: asyncio.sleep(0)):
        sessions = asyncio.run(generate_schedule(syllabus, 10, "science", dates))
    assert len(sessions) == 4
    assert sessions[0]["chapter"].startswith("Chapter 1")
    assert sessions[-1]["chapter"].startswith("Chapter 2")
