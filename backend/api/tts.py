"""POST /api/tts — text-to-speech via gTTS"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from gtts import gTTS
import io

router = APIRouter()

LANG_MAP = {"en": "en", "hi": "hi", "ml": "ml", "en-IN": "en", "hi-IN": "hi", "ml-IN": "ml"}


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


@router.post("/tts")
async def tts(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

    lang = LANG_MAP.get(req.language, "en")
    text = req.text[:1000]  # cap at 1000 chars to prevent abuse

    try:
        # Indian English accent for en; native voices for hi/ml
        tld = "co.in" if lang == "en" else "com"
        tts_obj = gTTS(text=text, lang=lang, tld=tld, slow=False)
        buf = io.BytesIO()
        tts_obj.write_to_fp(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
