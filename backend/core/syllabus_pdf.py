"""Extract a clean chapter list from an uploaded NCERT syllabus PDF"""

from google.genai import types

from core.keys import generate_content

EXTRACT_PROMPT = (
    "This is an NCERT syllabus document. Extract a clean chapter-by-chapter "
    "list as plain text, one chapter per line, no numbering, no extra "
    "commentary, no markdown."
)


def extract_syllabus_from_pdf(pdf_bytes: bytes) -> str:
    response = generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            EXTRACT_PROMPT,
        ],
    )
    return response.text.strip()
