from __future__ import annotations
from .http import get

# quick content sniff
_RSS_MARKERS = (b"<rss", b"<feed", b"\"version\":\"https://jsonfeed.org/version/1")

def looks_like_feed_bytes(b: bytes) -> bool:
    sniff = b[:20480].lower()
    return any(tag in sniff for tag in _RSS_MARKERS)

def validate_feed(url: str) -> bool:
    try:
        r = get(url)
        if r.status_code >= 400:
            return False
        return looks_like_feed_bytes(r.content)
    except Exception:
        return False
