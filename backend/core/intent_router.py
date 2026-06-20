"""Intent router — classifies teacher transcripts using Gemini 2.5 Flash"""

import os
import json
from google import genai
from google.genai import types

_client = None

INTENT_PROMPT = """You are the intent router for Saathi.AI, a voice-controlled educational assistant for Indian teachers.

AVAILABLE INTENTS:
1. concept_simplification — teacher wants an explanation of a concept with a visual
2. quiz_generation — teacher wants quiz questions generated
3. bilingual_translation — teacher wants text translated and displayed in two languages
4. activity_guide — teacher wants a timed classroom activity generated
5. unclear — cannot determine intent

SESSION CONTEXT:
Current grade: {current_grade}
Current subject: {current_subject}
Previous topic: {previous_topic}
Session language: {session_language}

TRANSCRIPT: "{transcript}"

Detect the language spoken. Infer grade and subject from transcript if stated; otherwise use session defaults.
Handle mixed-language input (Hinglish, Manglish) naturally.

CLASSIFICATION EXAMPLES:
- "explain X", "what is X", "X samjhao", "X simple banao" -> concept_simplification
- "give me N MCQ on X", "N questions on X", "quiz on X", "test the class on X", "make questions" -> quiz_generation
- "translate X", "X ko hindi mein", "say X in malayalam" -> bilingual_translation
- "N minute activity on X", "group activity", "pair task on X" -> activity_guide
Only use "unclear" if the request truly matches none of the four. Prefer a best-guess intent over unclear.

OUTPUT (strict JSON, no other text):
{{
  "intent": "concept_simplification | quiz_generation | bilingual_translation | activity_guide | unclear",
  "topic": "extracted topic or null",
  "grade": null,
  "subject": "extracted subject or null",
  "language": "en | hi | ml",
  "confidence": 0.0,
  "quiz_type": "mcq | true_false | short_answer | null",
  "question_count": null,
  "source_text": "text to translate (if bilingual_translation) or null",
  "duration_minutes": null,
  "activity_type": "group | pair | individual | null",
  "additional_params": {{}}
}}"""


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)


async def route_intent(transcript: str, session_context: dict) -> dict:
    from core.keys import generate_content
    prompt = INTENT_PROMPT.format(
        current_grade=session_context.get("grade", 10),
        current_subject=session_context.get("subject", "science"),
        previous_topic=session_context.get("previous_topic") or "none",
        session_language=session_context.get("language", "en"),
        transcript=transcript,
    )

    for attempt in range(3):
        try:
            response = generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            return _safe_parse(response.text)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)
            else:
                return {"intent": "unclear", "confidence": 0.0, "language": "en"}

    return {"intent": "unclear", "confidence": 0.0, "language": "en"}
