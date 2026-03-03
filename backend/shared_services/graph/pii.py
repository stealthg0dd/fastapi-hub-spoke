"""
PII detection and scrubbing utilities.

Used by the Security node in the chat graph to redact sensitive information
from LLM-generated responses before they are returned to the caller.

Patterns cover the most common PII types found in multi-venture contexts
(finance, health/IoT, retail, sports).  Extend _PATTERNS as needed.
"""

import re

# (compiled_regex, replacement_token) pairs — evaluated in order.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL]",
    ),
    # US / international phone numbers
    (
        re.compile(
            r"\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "[PHONE]",
    ),
    # US Social Security Numbers  (NNN-NN-NNNN)
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[SSN]",
    ),
    # Payment card numbers (13–19 digits, optional separators)
    (
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{1,4}\b"),
        "[CARD]",
    ),
    # IPv4 addresses
    (
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        "[IP]",
    ),
    # UK National Insurance numbers  (AB 12 34 56 C)
    (
        re.compile(r"\b[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b"),
        "[NI]",
    ),
    # Passport numbers (very rough — 1-2 letters + 6-7 digits)
    (
        re.compile(r"\b[A-Z]{1,2}\d{6,7}\b"),
        "[PASSPORT]",
    ),
]


def scrub(text: str) -> tuple[str, list[str]]:
    """
    Scan *text* for PII and replace each match with a token.

    Returns
    -------
    scrubbed : str
        The text with all detected PII replaced by tokens such as [EMAIL].
    detected_types : list[str]
        Unique PII category names found (e.g. ``["EMAIL", "PHONE"]``).
        Empty list means no PII was found.
    """
    detected: set[str] = set()
    for pattern, token in _PATTERNS:
        if pattern.search(text):
            label = token.strip("[]")
            detected.add(label)
            text = pattern.sub(token, text)
    return text, sorted(detected)
