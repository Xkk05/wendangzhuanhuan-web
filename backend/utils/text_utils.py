from __future__ import annotations

from pathlib import Path
from typing import Optional


COMMON_TEXT_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "gb18030",
    "gbk",
    "big5",
)


def decode_text_bytes(data: bytes, encoding: Optional[str] = None) -> str:
    """Decode uploaded text with common Chinese encodings before falling back."""
    candidates = []
    if encoding:
        candidates.append(encoding)
    candidates.extend(COMMON_TEXT_ENCODINGS)

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            return data.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue

    # Last resort: pick the least lossy replacement decode.
    best_text = data.decode("utf-8", errors="replace")
    best_score = best_text.count("\ufffd")
    for candidate in COMMON_TEXT_ENCODINGS:
        try:
            text = data.decode(candidate, errors="replace")
        except LookupError:
            continue
        score = text.count("\ufffd")
        if score < best_score:
            best_text = text
            best_score = score
    return best_text


def read_text_file(path: str, encoding: Optional[str] = None) -> str:
    return decode_text_bytes(Path(path).read_bytes(), encoding=encoding)


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def detect_tts_language(text: str, default: str = "zh-CN") -> str:
    if contains_cjk(text):
        return "zh-CN"
    return default or "en"
