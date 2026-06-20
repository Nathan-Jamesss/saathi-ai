"""Feature 4 — Hands-Free Activity Guide"""

import os
import json
from google import genai
from google.genai import types
from core.rag import retrieve_chunks

_client = None

ACTIVITY_PROMPT = """You are Saathi.AI, an educational co-pilot for Indian school teachers.

TASK: Generate a classroom activity guide on "{topic}" for Class {grade} students.
DURATION: {duration_minutes} minutes
ACTIVITY TYPE: {activity_type}
OUTPUT LANGUAGE: {language}

CONTEXT FROM NCERT (if available):
{ncert_chunks}

OUTPUT FORMAT (strict JSON):
{{
  "activity_title": "Title of the activity in {language}",
  "topic": "{topic}",
  "duration_minutes": {duration_minutes},
  "activity_type": "{activity_type}",
  "steps": [
    {{
      "step_number": 1,
      "title": "Short step title in {language}",
      "instruction": "Clear instruction for students in {language}",
      "duration_seconds": 120,
      "teacher_note": "Optional hint for teacher in English"
    }}
  ],
  "materials_needed": ["list of materials if any"],
  "expected_outcome": "What students should have learned"
}}

RULES:
- Steps must sum to exactly {duration_minutes} minutes (duration_seconds values sum to {duration_minutes}*60)
- Maximum 6 steps
- No special materials beyond chalk, paper, textbook
- Never include text outside the JSON object
"""


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _client


def _safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)


async def generate_activity(
    topic: str, grade: int, subject: str, language: str,
    duration_minutes: int = 10, activity_type: str = "group",
) -> dict:
    chunks = retrieve_chunks(topic, grade, subject, n_results=3)
    ncert_text = "\n\n".join(chunks) if chunks else "[No NCERT content]"

    prompt = ACTIVITY_PROMPT.format(
        topic=topic, grade=grade, subject=subject, language=language,
        duration_minutes=duration_minutes, activity_type=activity_type,
        ncert_chunks=ncert_text[:2000],
    )

    from core.keys import generate_content
    for attempt in range(3):
        try:
            response = generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    response_mime_type="application/json",
                    max_output_tokens=2048,
                ),
            )
            return _safe_parse(response.text)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)
            elif attempt == 2:
                raise

    return {
        "activity_title": f"{topic} Activity", "topic": topic,
        "duration_minutes": duration_minutes, "activity_type": activity_type,
        "steps": [], "materials_needed": [], "expected_outcome": "",
    }
