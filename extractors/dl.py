import re
from typing import Optional, List

def extract_dl(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return {
        "dl_number": _dl_number(text),
        "name": _name(lines),
        "dob": _dob(text),
    }

def _dl_number(text: str) -> Optional[str]:
    clean_text = text.replace(' ', '').replace('-', '')
    m = re.search(r'\b([A-Z]{2}[0-9]{13})\b', clean_text)
    if m:
        return m.group(1)
    m = re.search(r'(?:DL|Licence)\s*No\s*[:\-]?\s*([A-Z0-9\-\s]{10,20})', text, re.IGNORECASE)
    return m.group(1).strip() if m else None

def _dob(text: str) -> Optional[str]:
    m = re.search(r'(?:DOB|Date of Birth)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})', text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
    return m.group(1) if m else None

def _name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'(?i)\bname\b', line):
            parts = re.split(r':|-', line)
            if len(parts) > 1 and parts[-1].strip():
                return parts[-1].strip().title()
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s]+$', candidate):
                    return candidate.title()
    return None
