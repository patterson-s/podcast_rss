from __future__ import annotations
import urllib.parse
from typing import Optional
from ..http import get
from .apple import search_feed_by_title

OEMBED = "https://open.spotify.com/oembed"

def _title_from_oembed(url: str) -> Optional[str]:
    try:
        r = get(OEMBED + "?" + urllib.parse.urlencode({"url": url}))
        if r.status_code == 404:
            return None
        return r.json().get("title")
    except Exception:
        return None

def resolve_from_spotify_url(url: str) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (feed_url, notes). When no feed is found, notes may say 'likely exclusive'.
    """
    title = _title_from_oembed(url)
    if not title:
        return None, "No oEmbed title; may be exclusive or URL not a show"
    feed = search_feed_by_title(title)
    if feed:
        return feed, f"Matched by title: {title}"
    return None, f"No public RSS for '{title}' (likely exclusive)"
