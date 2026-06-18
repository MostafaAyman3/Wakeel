"""
Shared language detection utility.

Single source of truth for AR/EN auto-detection across all modules.
M1 currently has an inline copy in its intent classifier; new code (M3+)
should import from here to avoid duplication.

Usage:
    from agents.shared.language import detect_language

    lang = detect_language("فين الأوردر بتاعي؟")   # -> "ar"
    lang = detect_language("Where is my order?")    # -> "en"
"""

from __future__ import annotations

# Arabic Unicode block: U+0600–U+06FF
_ARABIC_START = "؀"
_ARABIC_END = "ۿ"


def detect_language(text: str) -> str:
    """Detect language from free text.

    Rule: if the text contains any character in the Arabic Unicode range
    (U+0600–U+06FF), it is treated as Arabic; otherwise English.

    Args:
        text: Raw user input.

    Returns:
        ``"ar"`` or ``"en"``.
    """
    if not text:
        return "en"
    return "ar" if any(_ARABIC_START <= c <= _ARABIC_END for c in text) else "en"
