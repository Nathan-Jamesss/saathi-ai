"""Image enrichment — Wikipedia REST summary + Wikimedia Commons fallback"""

import httpx
import logging

logger = logging.getLogger(__name__)

WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
COMMONS_API  = "https://commons.wikimedia.org/w/api.php"


UA = "Saathi.AI/1.0 (https://github.com/Nathan-Jamesss/saathi-ai; classroom education) httpx"


async def fetch_wikipedia_image(topic: str) -> dict:
    """Try Wikipedia summary thumbnail first; fall back to Wikimedia Commons search."""
    t = topic.strip()
    slug = (t[0].upper() + t[1:]).replace(" ", "_") if t else t

    async with httpx.AsyncClient(timeout=6.0, headers={"User-Agent": UA}) as client:
        # 1) Wikipedia page summary thumbnail
        try:
            r = await client.get(WIKI_SUMMARY.format(slug=slug), follow_redirects=True)
            if r.status_code == 200:
                data = r.json()
                thumb = data.get("thumbnail", {}).get("source")
                if thumb:
                    return {
                        "image_url": thumb,
                        "caption": data.get("description", "") or topic,
                        "extract": (data.get("extract", "") or "")[:300],
                        "source": "wikipedia",
                    }
        except Exception as e:
            logger.debug(f"Wikipedia summary failed for '{topic}': {e}")

        # 2) Wikimedia Commons image search (much wider coverage)
        try:
            img = await _commons_image(client, topic)
            if img:
                return {"image_url": img, "caption": topic, "extract": "", "source": "commons"}
        except Exception as e:
            logger.debug(f"Commons search failed for '{topic}': {e}")

    return {"image_url": None, "caption": "", "extract": "", "source": None}


async def _commons_image(client: httpx.AsyncClient, topic: str) -> str | None:
    """Search Wikimedia Commons for a file matching the topic; return a usable image URL."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{topic} diagram|illustration|photo",
        "gsrnamespace": "6",        # File namespace
        "gsrlimit": "5",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": "800",
    }
    r = await client.get(COMMONS_API, params=params)
    if r.status_code != 200:
        return None
    pages = (r.json().get("query") or {}).get("pages") or {}
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        if mime.startswith("image/") and mime not in ("image/svg+xml",):
            return info.get("thumburl") or info.get("url")
    return None
