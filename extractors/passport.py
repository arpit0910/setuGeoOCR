import re
from typing import Optional, List, Any

def extract_passport(text: str, detailed: List[Any] = None) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Try MRZ first (Bottom of the passport, extremely reliable)
    mrz_data = _parse_mrz(text)
    
    return {
        "passport_number": mrz_data.get("number") or _passport_number(text),
        "surname": mrz_data.get("surname") or _surname(lines),
        "given_names": mrz_data.get("given_names") or _given_names(lines),
        "dob": mrz_data.get("dob") or _dob(text),
        "expiry": mrz_data.get("expiry"),
        "mrz": mrz_data.get("raw")
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

def _dob(text: str) -> Optional[str]:
    m = re.search(r'Date of Birth\s*(\d{2}/\d{2}/\d{4})', text, re.I)
    return m.group(1) if m else None

def _parse_mrz(text: str) -> dict:
    # Basic MRZ parser for Indian Passport (TD3 format)
    # P<INDNAME<<GIVEN<NAMES<<<<<<<<<<<<<<<<<<<<<<<<
    # NUM8<<<<7IND800101M250101<<<<<<<<<<<<<<06
    m = re.search(r'P<IND([A-Z<]+)\n([A-Z0-9<]+)', text.upper().replace(' ', ''))
    if not m: return {}
    
    line1 = m.group(1)
    line2 = m.group(2)
    
    parts = line1.split('<<')
    surname = parts[0].replace('<', ' ').strip()
    given = parts[1].replace('<', ' ').strip() if len(parts) > 1 else ""
    
    return {
        "surname": surname,
        "given_names": given,
        "number": line2[:9].replace('<', ''),
        "dob": line2[13:19],
        "expiry": line2[21:27],
        "raw": f"{line1}\n{line2}"
    }
