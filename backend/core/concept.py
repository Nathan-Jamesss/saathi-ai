"""Feature 1 — Live Concept Simplification"""

import os
import json
from google import genai
from google.genai import types
from core.rag       import retrieve_chunks
from core.wikipedia import fetch_wikipedia_image

_client = None

CONCEPT_PROMPT = """You are Saathi.AI, an educational co-pilot for Indian school teachers.

CONTEXT FROM NCERT TEXTBOOK (Class {grade}, {subject}):
{ncert_chunks}

TASK: Generate a classroom explanation of "{topic}" for Class {grade} students.

OUTPUT LANGUAGE: {language} (use natural code-mixing with English for technical terms)
{regen_note}

OUTPUT FORMAT (strict JSON):
{{
  "explanation": "2-3 paragraph explanation in {language}, calibrated to Class {grade} level. Use simple analogies. Technical terms in English are OK.",
  "key_points": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "mermaid_diagram": "A valid Mermaid.js flowchart string. Use graph TD. Keep node labels SHORT (max 4 words, no special chars except spaces). Example: graph TD\\n  A[Sunlight] --> B[Chlorophyll]\\n  B --> C[Glucose produced]",
  "analogy": "One memorable real-life analogy in {language}",
  "grade_calibration_note": "One sentence confirming calibration for Class {grade}"
}}

RULES:
- Never include text outside the JSON object
- Mermaid: use only graph TD, simple arrows -->, short labels, no parentheses in node labels
- Technical terms stay in English even in Malayalam/Hindi output
- If no NCERT context: note "[General knowledge — verify with NCERT]" in grade_calibration_note
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


async def generate_concept(topic: str, grade: int, subject: str, language: str, regenerate: bool = False) -> dict:
    chunks = retrieve_chunks(topic, grade, subject, n_results=5)
    ncert_text = "\n\n".join(chunks) if chunks else "[No NCERT content found — using general knowledge]"

    wiki = await fetch_wikipedia_image(topic)

    regen_note = "\nNOTE: Previous response was unsatisfactory. Generate a DIFFERENT explanation with a new diagram.\n" if regenerate else ""

    prompt = CONCEPT_PROMPT.format(
        grade=grade, subject=subject,
        ncert_chunks=ncert_text[:3000],
        topic=topic, language=language,
        regen_note=regen_note,
    )

    from core.keys import generate_content
    for attempt in range(3):
        try:
            response = generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    response_mime_type="application/json",
                    max_output_tokens=2048,
                ),
            )
            data = _safe_parse(response.text)
            data["wikipedia_image_url"]     = wiki.get("image_url") if wiki else None
            data["wikipedia_image_caption"] = (wiki.get("caption") or (wiki.get("extract") or "")[:120]) if wiki else ""
            return data
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)
            elif attempt == 2:
                raise

    return {"explanation": "Could not generate content.", "key_points": [], "mermaid_diagram": "", "analogy": ""}
