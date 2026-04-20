import re
from typing import Optional


def extract_pan(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return {
        "pan_number":   _pan_number(text),
        "name":         _name(lines),
        "father_name":  _father_name(lines),
        "dob":          _dob(text),
        "card_type":    _card_type(text),
    }


# ── field extractors ─────────────────────────────────────────────────────────

def _pan_number(text: str) -> Optional[str]:
    match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
    return match.group(1) if match else None


def _dob(text: str) -> Optional[str]:
    for pattern in [
        r'\b(\d{2}/\d{2}/\d{4})\b',
        r'\b(\d{2}-\d{2}-\d{4})\b',
        r'\b(\d{2}\.\d{2}\.\d{4})\b',
    ]:
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    return None


def _name(lines: list) -> Optional[str]:
    # Strategy 1: line immediately after a "Name" label
    for i, line in enumerate(lines):
        if re.fullmatch(r'(?i)name\s*:?', line.strip()):
            if i + 1 < len(lines):
                candidate = lines[i + 1]
                if _looks_like_name(candidate):
                    return candidate.title()

    # Strategy 2: first ALL-CAPS multi-word line (typical for PAN)
    for line in lines:
        if re.match(r'^[A-Z][A-Z\s\.]{4,}$', line) and len(line.split()) >= 2:
            return line.title()

    return None


def _father_name(lines: list) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r"father'?s?\s*name", line, re.IGNORECASE):
            if i + 1 < len(lines):
                candidate = lines[i + 1]
                if _looks_like_name(candidate):
                    return candidate.title()
    return None


def _card_type(text: str) -> str:
    upper = text.upper()
    mapping = {
        "Individual":  ["INDIVIDUAL"],
        "Company":     ["COMPANY"],
        "HUF":         ["HUF", "HINDU UNDIVIDED"],
        "Firm":        ["FIRM", "PARTNERSHIP"],
        "Trust":       ["TRUST"],
        "AOP":         ["ASSOCIATION OF PERSONS", "AOP"],
        "BOI":         ["BODY OF INDIVIDUALS", "BOI"],
    }
    for card_type, keywords in mapping.items():
        if any(kw in upper for kw in keywords):
            return card_type
    return "Individual"


# ── utility ──────────────────────────────────────────────────────────────────

def _looks_like_name(text: str) -> bool:
    return bool(re.match(r'^[A-Za-z][A-Za-z\s\.]{3,}$', text.strip()))
