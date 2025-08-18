from __future__ import annotations
import urllib.parse
from bs4 import BeautifulSoup
from ..http import get
from ..validators import validate_feed

RSS_MIME_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/rdf+xml",
    "application/feed+json",
    "text/xml",
    "application/xml",
}

def resolve_from_generic_page(url: str) -> str | None:
    try:
        r = get(url)
        if r.status_code >= 400:
            return None
        base = r.url  # after redirects
        soup = BeautifulSoup(r.text, "html.parser")

        # 1) <link rel="alternate" ...>
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel") or []).lower()
            typ = (link.get("type") or "").lower()
            href = link.get("href")
            if not href:
                continue
            if "alternate" in rel and (typ in RSS_MIME_TYPES or "rss" in typ or "atom" in typ or ("json" in typ and "feed" in typ)):
                candidate = urllib.parse.urljoin(base, href)
                if validate_feed(candidate):
                    return candidate

        # 2) Anchors that smell like feeds
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = (a.get_text() or "").lower()
            if any(tok in href.lower() for tok in ("rss", "atom", "feed.xml", "podcast.xml")) or "rss" in text or "feed" in text:
                candidate = urllib.parse.urljoin(base, href)
                if validate_feed(candidate):
                    return candidate

        # 3) Heuristic paths on same origin
        parsed = urllib.parse.urlparse(base)
        for suffix in ("/feed", "/feed.xml", "/rss", "/rss.xml", "/podcast.xml", "/podcast/feed"):
            candidate = f"{parsed.scheme}://{parsed.netloc}{suffix}"
            if validate_feed(candidate):
                return candidate
    except Exception:
        return None
    return None
