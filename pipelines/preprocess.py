"""Light, model-agnostic preprocessing.

Transformer inputs keep case, punctuation, emoji and stopwords. Only the
dedup key is aggressively normalized.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

_WS = re.compile(r"\s+")
_URL = re.compile(r"https?://\S+")


def normalize_for_model(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _URL.sub("<url>", text)
    return _WS.sub(" ", text).strip()


def dedup_key(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).casefold()
    t = _URL.sub("", t)
    t = re.sub(r"[^\w\s]", "", t)
    t = _WS.sub(" ", t).strip()
    if not t:
        # emoji/punctuation-only comment: keep the symbols so "🔥" != "😂"
        t = "sym:" + _WS.sub("", unicodedata.normalize("NFKC", text))
    return hashlib.sha256(t.encode()).hexdigest()
