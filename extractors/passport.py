import re
from typing import Optional, List

def extract_passport(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return {
        "passport_number": _passport_number(text),
        "surname": _surname(lines),
        "given_names": _given_names(lines),
    }

def _passport_number(text: str) -> Optional[str]:
    m = re.search(r'\b([A-Z][0-9]{7})\b', text)
    return m.group(1) if m else None

def _surname(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'(?i)surname', line):
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s]+$', candidate):
                    return candidate.upper()
    return None

def _given_names(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'(?i)given name', line):
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s]+$', candidate):
                    return candidate.title()
    return None
