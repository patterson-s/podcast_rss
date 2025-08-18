from __future__ import annotations
import requests

UA = "podfeedfinder/0.1 (+https://github.com/yourname/podfeedfinder)"
HEADERS = {"User-Agent": UA, "Accept": "*/*"}
TIMEOUT = 10

def get(url: str, *, allow_redirects: bool = True, headers: dict | None = None) -> requests.Response:
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    return requests.get(url, headers=h, timeout=TIMEOUT, allow_redirects=allow_redirects)
