"""Read a school's own timetable sheet (photo or PDF) and pull out which
weekdays a given grade/subject actually meets."""

import json

from google.genai import types

from core.keys import generate_content

EXTRACT_PROMPT = """This is a school class timetable for an Indian school.

Find the rows/columns for Class {grade} {subject} and work out which days of
the week that class actually meets.

OUTPUT (strict JSON, no other text):
{{
  "weekdays": [0, 2, 4],
  "note": "one short line naming the days and periods you found, e.g. 'Mon/Wed/Fri, period 3'"
}}

"weekdays" uses Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4,
Saturday=5, Sunday=6. Include each day only once, sorted.
If you genuinely cannot find this class in the timetable, return an empty
"weekdays" list and say so in "note".
"""


def _safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)


def extract_timetable(file_bytes: bytes, mime_type: str, grade: int, subject: str) -> dict:
    response = generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            EXTRACT_PROMPT.format(grade=grade, subject=subject),
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    data = _safe_parse(response.text)
    weekdays = sorted({int(d) for d in data.get("weekdays", []) if 0 <= int(d) <= 6})
    return {"weekdays": weekdays, "note": data.get("note", "")}
