from __future__ import annotations
import re, urllib.parse
from typing import Optional
from ..http import get
from ..validators import validate_feed

APPLE_LOOKUP = "https://itunes.apple.com/lookup"
APPLE_SEARCH = "https://itunes.apple.com/search"
APPLE_ID_RE = re.compile(r"/id(\d+)")

def extract_id(url: str) -> Optional[str]:
    m = APPLE_ID_RE.search(url)
    return m.group(1) if m else None

def lookup_feed_by_id(apple_id: str) -> Optional[str]:
    try:
        resp = get(APPLE_LOOKUP + "?" + urllib.parse.urlencode({"id": apple_id}))
        data = resp.json()
        for item in data.get("results", []):
            feed = item.get("feedUrl")
            if feed and validate_feed(feed):
                return feed
    except Exception:
        return None
    return None

def search_feed_by_title(title: str) -> Optional[str]:
    params = {"term": title, "media": "podcast", "limit": 5}
    try:
        resp = get(APPLE_SEARCH + "?" + urllib.parse.urlencode(params))
        data = resp.json()
        # Prefer exact-ish matches, then validate
        scored = []
        q = _norm(title)
        for it in data.get("results", []):
            feed = it.get("feedUrl")
            t = it.get("trackName", "")
            score = _score(_norm(t), q)
            if feed:
                scored.append((score, feed))
        scored.sort(reverse=True, key=lambda x: x[0])
        for _, feed in scored:
            if validate_feed(feed):
                return feed
    except Exception:
        return None
    return None

def resolve_from_apple_url(url: str) -> Optional[str]:
    apple_id = extract_id(url)
    return lookup_feed_by_id(apple_id) if apple_id else None

def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", (s or "").strip().lower())

def _score(a: str, b: str) -> int:
    if not a or not b:
        return 0
    score = 0
    if a == b:
        score += 5
    if a in b or b in a:
        score += 2
    return score
