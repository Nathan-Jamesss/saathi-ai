"""Feature 2 — Voice-Triggered Quiz Generation"""

import os
import json
from typing import List
from google import genai
from google.genai import types
from core.rag import retrieve_chunks

_client = None

QUIZ_PROMPT = """You are Saathi.AI, an educational co-pilot for Indian school teachers.

CONTEXT FROM NCERT TEXTBOOK (Class {grade}, {subject}):
{ncert_chunks}

TASK: Generate {count} {quiz_type} questions on "{topic}" for Class {grade}.

OUTPUT LANGUAGE: {language} (technical terms stay in English)
{regen_note}
PREVIOUS TOPICS IN SESSION (avoid duplicate questions): {history}

OUTPUT FORMAT (strict JSON):
{{
  "questions": [
    {{
      "number": 1,
      "question": "question text in {language}",
      "type": "{quiz_type}",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "explanation": "one sentence explanation in {language}"
    }}
  ],
  "topic": "{topic}",
  "grade": {grade},
  "quiz_type": "{quiz_type}",
  "total_questions": {count}
}}

RULES:
- For true_false: omit "options", set correct_answer to "True" or "False"
- For short_answer: omit "options" and "correct_answer", include "model_answer" instead
- Mix difficulty: ~40% easy, ~40% medium, ~20% hard
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


async def generate_quiz(
    topic: str, grade: int, subject: str, language: str,
    quiz_type: str = "mcq", count: int = 5,
    history: List[str] = None, regenerate: bool = False,
) -> dict:
    chunks = retrieve_chunks(topic, grade, subject, n_results=5)
    ncert_text = "\n\n".join(chunks) if chunks else "[No NCERT content found]"
    regen_note = "\nNOTE: Previous response was unsatisfactory. Generate DIFFERENT questions.\n" if regenerate else ""

    prompt = QUIZ_PROMPT.format(
        grade=grade, subject=subject, ncert_chunks=ncert_text[:3000],
        topic=topic, language=language, quiz_type=quiz_type, count=count,
        history=", ".join(history or []) or "none", regen_note=regen_note,
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

    return {"questions": [], "topic": topic, "grade": grade, "quiz_type": quiz_type, "total_questions": 0}
