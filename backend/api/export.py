"""POST /api/export — returns session data as JSON for client-side PDF generation"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter()


class ExportRequest(BaseModel):
    session: Dict[str, Any]


@router.post("/export")
async def export(req: ExportRequest):
    """Returns the session data; PDF is generated client-side by jsPDF."""
    return {"ok": True, "session": req.session}
