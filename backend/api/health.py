"""GET /api/health"""

from fastapi import APIRouter
from core.rag import is_chroma_ready

router = APIRouter()


@router.get("/health")
async def health():
    import os

    gemini_ready = bool(os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY"))

    return {
        "status": "ok",
        "chroma_ready": is_chroma_ready(),
        "gemini_ready": gemini_ready,
    }
