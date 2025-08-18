from __future__ import annotations
import re, urllib.parse
from typing import Optional
from ..core import Result
from .apple import resolve_from_apple_url, search_feed_by_title
from .spotify import resolve_from_spotify_url
from .autodiscover import resolve_from_generic_page

def find_feed(input_str: str) -> Result:
    s = (input_str or "").strip()
    if not s:
        return Result(s, "error", None, notes="empty input")

    is_url = re.match(r"^https?://", s, re.I) is not None
    if is_url:
        host = urllib.parse.urlparse(s).netloc.lower()

        if "podcasts.apple.com" in host:
            feed = resolve_from_apple_url(s)
            if feed:
                return Result(s, "found", feed, "apple_lookup")
            # fallback: try page title via Apple search
            # (kept minimal here — Streamlit UI also exposes a free-form search)
            return Result(s, "not_found", None, "apple_lookup", "No feed from Apple Lookup")

        if "open.spotify.com" in host:
            feed, notes = resolve_from_spotify_url(s)
            if feed:
                return Result(s, "found", feed, "spotify_title_match", notes)
            return Result(s, "exclusive_or_unsupported", None, "spotify_title_match", notes)

        # generic page
        feed = resolve_from_generic_page(s)
        if feed:
            return Result(s, "found", feed, "autodiscovery")
        return Result(s, "not_found", None, "autodiscovery", "No feed discovered")

    # Non-URL input → treat as search term via Apple
    feed = search_feed_by_title(s)
    if feed:
        return Result(s, "found", feed, "apple_search")
    return Result(s, "not_found", None, "apple_search", "No feed for search term")
