"""Mention parsing for team comments (spec FR-COM-5/6)."""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"@([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


def extract_mentioned_emails(text: str) -> list[str]:
    """Pull `@user@host.tld` tokens from comment text (deduplicated, order-preserving)."""
    seen: dict[str, None] = {}
    for match in _EMAIL_RE.findall(text):
        seen.setdefault(match.lower(), None)
    return list(seen.keys())
