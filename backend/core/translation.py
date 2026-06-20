"""Feature 3 — Bilingual Dictation & Translation"""

import os
import json
from google import genai
from google.genai import types

_client = None

TRANSLATION_PROMPT = """You are Saathi.AI, a bilingual educational assistant for Indian classrooms.

TASK: Translate the following text accurately.
SOURCE TEXT: {source_text}
SOURCE LANGUAGE: {source_language}
TARGET LANGUAGE: {target_language}

OUTPUT FORMAT (strict JSON):
{{
  "original_text": "{source_text}",
  "original_language": "{source_language}",
  "translated_text": "accurate translation in {target_language}",
  "target_language": "{target_language}",
  "transliteration": "romanized pronunciation guide — ONLY for Malayalam output, otherwise empty string",
  "notes": "translation notes if any, otherwise empty string"
}}

RULES:
- Scientific/technical terms with no standard translation → keep in English
- Transliteration ONLY for Malayalam output
- Natural sentence structure, not word-for-word
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


async def generate_translation(source_text: str, source_language: str, target_language: str) -> dict:
    prompt = TRANSLATION_PROMPT.format(
        source_text=source_text,
        source_language=source_language,
        target_language=target_language,
    )

    from core.keys import generate_content
    for attempt in range(3):
        try:
            response = generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    max_output_tokens=1024,
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
        "original_text": source_text, "original_language": source_language,
        "translated_text": "Translation failed.", "target_language": target_language,
        "transliteration": "", "notes": "",
    }
