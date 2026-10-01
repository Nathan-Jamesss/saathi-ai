"""Google Docs API calls — create a notes doc and append to it."""

import httpx

DOCS_ENDPOINT = "https://docs.googleapis.com/v1/documents"


def doc_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def create_doc(access_token: str, title: str) -> dict:
    resp = httpx.post(
        DOCS_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": title},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"doc_id": data["documentId"], "doc_url": doc_url(data["documentId"])}


def append_text(access_token: str, doc_id: str, text: str) -> None:
    """Append to the end of the doc. endOfSegmentLocation lets Google place
    the text at the end without us tracking the current index."""
    resp = httpx.post(
        f"{DOCS_ENDPOINT}/{doc_id}:batchUpdate",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "requests": [
                {
                    "insertText": {
                        "endOfSegmentLocation": {"segmentId": ""},
                        "text": text if text.endswith("\n") else text + "\n",
                    }
                }
            ]
        },
        timeout=30,
    )
    resp.raise_for_status()
