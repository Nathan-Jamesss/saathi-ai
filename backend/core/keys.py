"""Central Gemini key pool with rotation on 429 (quota exhaustion).

Set GEMINI_API_KEYS in .env as a comma-separated list to rotate across
multiple Google Cloud projects (each project = its own 20/day free quota).
Falls back to single GEMINI_API_KEY if the list is not set.
"""

import os
import logging
from google import genai

logger = logging.getLogger(__name__)

_clients = []
_idx = 0


def _load():
    global _clients
    if _clients:
        return
    raw = os.environ.get("GEMINI_API_KEYS", "") or os.environ.get("GEMINI_API_KEY", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("No GEMINI_API_KEYS / GEMINI_API_KEY set")
    _clients = [genai.Client(api_key=k) for k in keys]
    logger.info(f"Loaded {len(_clients)} Gemini key(s) for rotation")


def _is_quota(e: Exception) -> bool:
    s = str(e)
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def generate_content(**kwargs):
    """Call models.generate_content, rotating keys on quota errors.
    Raises the last error if every key is exhausted."""
    global _idx
    _load()
    n = len(_clients)
    last = None
    for step in range(n):
        client = _clients[_idx]
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            last = e
            if _is_quota(e):
                logger.warning(f"Key #{_idx} quota hit, rotating")
                _idx = (_idx + 1) % n
                continue
            raise
    raise last


def embed_content(**kwargs):
    """Call models.embed_content, rotating keys on quota errors."""
    global _idx
    _load()
    n = len(_clients)
    last = None
    for step in range(n):
        client = _clients[_idx]
        try:
            return client.models.embed_content(**kwargs)
        except Exception as e:
            last = e
            if _is_quota(e):
                _idx = (_idx + 1) % n
                continue
            raise
    raise last


def key_count() -> int:
    _load()
    return len(_clients)
