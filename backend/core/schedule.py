"""AI-generated class timetable — dates computed deterministically,
Gemini only maps syllabus chapters onto the computed class slots."""

import json
from datetime import date, timedelta
from typing import List

from google.genai import types

from core.keys import generate_content

SCHEDULE_PROMPT = """You are planning a teaching schedule for Class {grade} {subject}.

SYLLABUS (chapters to cover, in order):
{syllabus}

There are exactly {slot_count} class sessions available. Map the syllabus
onto these {slot_count} sessions in order: split long chapters across
multiple sessions if there are more sessions than chapters, or group short
chapters together if there are more chapters than sessions. Every session
must be covered.

OUTPUT (strict JSON, a list of exactly {slot_count} objects, no other text):
[
  {{"chapter": "chapter name", "focus": "one short phrase on what this specific session covers"}},
  ...
]
"""


def _safe_parse(text: str) -> list:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)


def compute_class_dates(start_date: date, end_date: date, classes_per_week: int) -> List[date]:
    classes_per_week = max(1, min(7, classes_per_week))
    weekdays = sorted({(i * 7 // classes_per_week) % 7 for i in range(classes_per_week)})

    dates = []
    day = start_date
    while day <= end_date:
        if day.weekday() in weekdays:
            dates.append(day)
        day += timedelta(days=1)
    return dates


async def generate_schedule(syllabus_content: str, grade: int, subject: str, class_dates: List[date]) -> list:
    prompt = SCHEDULE_PROMPT.format(
        grade=grade, subject=subject, syllabus=syllabus_content, slot_count=len(class_dates)
    )

    for attempt in range(3):
        try:
            response = generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            sessions = _safe_parse(response.text)
            return sessions[: len(class_dates)]
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)
            elif attempt == 2:
                raise
    return []
