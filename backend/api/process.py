"""POST /api/process — main pipeline endpoint"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from core.intent_router import route_intent
from core.concept       import generate_concept
from core.quiz          import generate_quiz
from core.translation   import generate_translation
from core.activity      import generate_activity

router = APIRouter()


class SessionContext(BaseModel):
    grade: int = 10
    subject: str = "science"
    language: str = "en"
    previous_topic: Optional[str] = None
    history: List[str] = []


class ProcessRequest(BaseModel):
    transcript: str
    session: SessionContext = SessionContext()
    regenerate: bool = False


@router.post("/process")
async def process(req: ProcessRequest):
    transcript = req.transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript is empty")

    # Step 1: Route intent
    intent_data = await route_intent(transcript, req.session.dict())

    intent     = intent_data.get("intent", "unclear")
    topic      = intent_data.get("topic") or req.session.previous_topic or "unknown"
    grade      = intent_data.get("grade") or req.session.grade
    subject    = intent_data.get("subject") or req.session.subject
    language   = intent_data.get("language") or req.session.language
    confidence = intent_data.get("confidence", 0.0)

    if intent == "unclear" or confidence < 0.45:
        return {
            "intent": "unclear",
            "detected_language": language,
            "topic": None,
            "grade": grade,
            "subject": subject,
            "content": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": str(uuid.uuid4()),
        }

    # Step 2: Dispatch to feature handler
    content = {}
    if intent == "concept_simplification":
        content = await generate_concept(topic, grade, subject, language, req.regenerate)
    elif intent == "quiz_generation":
        content = await generate_quiz(
            topic, grade, subject, language,
            intent_data.get("quiz_type", "mcq"),
            intent_data.get("question_count", 5),
            req.session.history,
            req.regenerate,
        )
    elif intent == "bilingual_translation":
        content = await generate_translation(
            intent_data.get("source_text", transcript),
            intent_data.get("source_language", "en"),
            intent_data.get("target_language", "ml" if language == "en" else "en"),
        )
    elif intent == "activity_guide":
        content = await generate_activity(
            topic, grade, subject, language,
            intent_data.get("duration_minutes", 10),
            intent_data.get("activity_type", "group"),
        )

    return {
        "intent": intent,
        "detected_language": language,
        "topic": topic,
        "grade": grade,
        "subject": subject,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(uuid.uuid4()),
    }
