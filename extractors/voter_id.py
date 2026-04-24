import re
from typing import Optional, List

def extract_voter_id(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return {
        "voter_id_number": _voter_id_number(text),
        "name": _name(lines),
        "father_name": _father_name(lines),
        "dob": _dob(text),
    }

def _voter_id_number(text: str) -> Optional[str]:
    m = re.search(r'\b([A-Z]{3}[0-9]{7})\b', text)
    return m.group(1) if m else None

def _dob(text: str) -> Optional[str]:
    m = re.search(r'(?:DOB|Date of Birth|Age)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})', text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def _name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'(?i)elector.*name|name', line):
            parts = re.split(r':|-', line)
            if len(parts) > 1 and parts[-1].strip():
                return parts[-1].strip().title()
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s]+$', candidate):
                    return candidate.title()
    return None

def _father_name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'(?i)father|husband', line):
            parts = re.split(r':|-', line)
            if len(parts) > 1 and parts[-1].strip():
                return parts[-1].strip().title()
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s]+$', candidate):
                    return candidate.title()
    return None
