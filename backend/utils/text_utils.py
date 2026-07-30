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


TTS_LANGUAGE_ALIASES = {
    "zh": "zh-CN", "zh-cn": "zh-CN", "zh_cn": "zh-CN", "zh-hans": "zh-CN",
    "zh-tw": "zh-TW", "zh_tw": "zh-TW", "zh-hant": "zh-TW",
    "pt-br": "pt", "pt_br": "pt", "fil": "tl",
}

TTS_SUPPORTED_LANGUAGES = {
    "ar", "de", "en", "es", "fa", "fr", "he", "hi", "id", "it", "ja", "ko",
    "ms", "nl", "pl", "pt", "ru", "sw", "ta", "th", "tl", "tr", "uk", "ur", "vi",
    "zh-CN", "zh-TW",
}


def _contains_range(text: str, start: str, end: str) -> bool:
    return any(start <= char <= end for char in text)


def detect_tts_language(text: str, default: str = "en") -> str:
    if _contains_range(text, "\u3040", "\u30ff"):
        return "ja"
    if _contains_range(text, "\uac00", "\ud7af"):
        return "ko"
    if _contains_range(text, "\u0600", "\u06ff"):
        return "ar"
    if _contains_range(text, "\u0590", "\u05ff"):
        return "he"
    if _contains_range(text, "\u0900", "\u097f"):
        return "hi"
    if _contains_range(text, "\u0b80", "\u0bff"):
        return "ta"
    if _contains_range(text, "\u0e00", "\u0e7f"):
        return "th"
    if _contains_range(text, "\u0400", "\u04ff"):
        lowered = text.lower()
        return "uk" if any(char in lowered for char in "іїєґ") else "ru"
    if contains_cjk(text):
        return "zh-CN"

    lowered = f" {text.lower()} "
    language_markers = {
        "es": (" el ", " la ", " que ", " para ", " una "),
        "fr": (" le ", " la ", " les ", " une ", " des "),
        "de": (" der ", " die ", " das ", " und ", " ist "),
        "pt": (" que ", " para ", " uma ", " não ", "ção"),
        "it": (" il ", " che ", " una ", " per ", "zione"),
        "nl": (" het ", " een ", " van ", " voor ", " niet "),
        "tr": (" bir ", " ve ", " için ", " değil ", "lar "),
        "vi": (" và ", " của ", " không ", " cho ", " tiếng "),
        "id": (" dan ", " yang ", " untuk ", " tidak ", " dengan "),
    }
    scores = {
        language: sum(marker in lowered for marker in markers)
        for language, markers in language_markers.items()
    }
    best_language = max(scores, key=scores.get)
    if scores[best_language] > 0:
        return best_language
    return default or "en"


def normalize_tts_language(language: Optional[str], text: str = "") -> str:
    raw = str(language or "").strip()
    normalized = TTS_LANGUAGE_ALIASES.get(raw.lower(), raw)
    if normalized in TTS_SUPPORTED_LANGUAGES:
        return normalized
    if normalized.lower() in TTS_SUPPORTED_LANGUAGES:
        return normalized.lower()
    return detect_tts_language(text, default="en")
