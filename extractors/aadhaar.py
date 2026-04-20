import re
from typing import Optional


def extract_aadhaar(text: str, side: str) -> dict:
    if side == "aadhaar_front":
        return _extract_front(text)
    if side == "aadhaar_back":
        return _extract_back(text)
    return {}


# ── front ────────────────────────────────────────────────────────────────────

def _extract_front(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return {
        "aadhaar_number": _aadhaar_number(text),
        "name":           _name_front(lines),
        "dob":            _dob(text),
        "gender":         _gender(text),
        "year_of_birth":  _year_of_birth(text),
    }


# ── back ─────────────────────────────────────────────────────────────────────

def _extract_back(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    address = _address(lines)
    return {
        "aadhaar_number": _aadhaar_number(text),
        "address":        address,
        "pincode":        _pincode(text),
    }


# ── shared field extractors ──────────────────────────────────────────────────

def _aadhaar_number(text: str) -> Optional[str]:
    # 12-digit number, may be spaced as XXXX XXXX XXXX
    m = re.search(r'\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b', text)
    if m:
        return re.sub(r'[\s\-]', '', m.group(1))
    return None


def _dob(text: str) -> Optional[str]:
    for pattern in [
        r'(?:DOB|Date of Birth)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})',
        r'(?:DOB|Date of Birth)\s*[:\-]?\s*(\d{2}-\d{2}-\d{4})',
        r'\b(\d{2}/\d{2}/\d{4})\b',
        r'\b(\d{2}-\d{2}-\d{4})\b',
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _year_of_birth(text: str) -> Optional[str]:
    m = re.search(r'(?:YOB|Year of Birth)\s*[:\-]?\s*(\d{4})', text, re.IGNORECASE)
    return m.group(1) if m else None


def _gender(text: str) -> Optional[str]:
    upper = text.upper()
    if re.search(r'\bFEMALE\b', upper):
        return "Female"
    if re.search(r'\bMALE\b', upper):
        return "Male"
    if re.search(r'\bTRANSGENDER\b', upper):
        return "Transgender"
    return None


def _name_front(lines: list) -> Optional[str]:
    _SKIP = {
        "GOVERNMENT", "INDIA", "UIDAI", "UNIQUE", "IDENTIFICATION",
        "AUTHORITY", "DOB", "MALE", "FEMALE", "TRANSGENDER", "YEAR",
        "YOB", "ENROLMENT",
    }

    for line in lines:
        words = line.split()
        # Name lines: 2-4 words, only letters/dots/spaces, not a skip word
        if not (2 <= len(words) <= 5):
            continue
        if any(w.upper() in _SKIP for w in words):
            continue
        if re.match(r'^[A-Za-z][A-Za-z\s\.]{3,}$', line):
            return line.title()
    return None


def _address(lines: list) -> Optional[str]:
    _TRIGGERS = {
        "S/O", "D/O", "W/O", "C/O", "H.NO", "H.NO.", "HOUSE NO",
        "FLAT", "PLOT", "VILLAGE", "DIST", "DISTRICT", "STATE",
        "PINCODE", "PIN CODE", "POST", "STREET", "ROAD", "NAGAR",
        "COLONY", "MOHALLA", "WARD", "BLOCK", "SECTOR",
    }
    _NOISE = {"GOVERNMENT", "INDIA", "UIDAI", "UNIQUE", "IDENTIFICATION", "AUTHORITY"}

    collecting = False
    addr_lines = []

    for line in lines:
        upper = line.upper()
        if any(t in upper for t in _TRIGGERS):
            collecting = True
        if collecting:
            if any(n in upper for n in _NOISE):
                continue
            if re.fullmatch(r'\d{12}', line.replace(" ", "")):  # raw Aadhaar number
                continue
            addr_lines.append(line)
            if re.search(r'\b\d{6}\b', line):  # pincode signals end of address
                break

    return ", ".join(addr_lines) if addr_lines else None


def _pincode(text: str) -> Optional[str]:
    m = re.search(r'\b(\d{6})\b', text)
    return m.group(1) if m else None
