from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Result:
    input: str
    status: str               # "found" | "not_found" | "exclusive_or_unsupported" | "error"
    feed_url: Optional[str]
    source: Optional[str] = None
    notes: Optional[str] = None
