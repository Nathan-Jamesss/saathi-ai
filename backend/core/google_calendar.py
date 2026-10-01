"""Google Calendar API — put a teacher's generated classes on their own calendar."""

import httpx

CALENDAR_ENDPOINT = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def upsert_class_event(
    access_token: str,
    event_id: str,
    summary: str,
    description: str,
    day: str,
) -> str:
    """Create the event, or update it in place if we already made one for this
    class. Returns the Google event id to store against the class.

    All-day event: Google's end date is exclusive, so a single-day event ends
    the following day.
    """
    from datetime import date, timedelta

    end_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    body = {
        "summary": summary,
        "description": description,
        "start": {"date": day},
        "end": {"date": end_day},
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    if event_id:
        resp = httpx.put(
            f"{CALENDAR_ENDPOINT}/{event_id}", headers=headers, json=body, timeout=30
        )
        if resp.status_code == 404:
            # Teacher deleted it on their side — make a fresh one.
            event_id = ""
        else:
            resp.raise_for_status()
            return resp.json()["id"]

    resp = httpx.post(CALENDAR_ENDPOINT, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def delete_class_event(access_token: str, event_id: str) -> None:
    if not event_id:
        return
    resp = httpx.delete(
        f"{CALENDAR_ENDPOINT}/{event_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if resp.status_code not in (200, 204, 404, 410):
        resp.raise_for_status()
