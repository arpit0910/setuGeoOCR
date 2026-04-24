import re
from typing import Optional, List


def extract_pan(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    clean_lines = []
    for l in lines:
        l = re.sub(r'[^a-zA-Z0-9\s\./\-]', '', l).strip()
        if len(l) > 2:
            clean_lines.append(l)

    return {
        "pan_number":   _pan_number(text),
        "name":         _name(clean_lines) or _name_fallback(lines),
        "father_name":  _father_name(clean_lines) or _father_name_fallback(lines),
        "dob":          _dob(text),
        "card_type":    _card_type(text),
    }


# ── field extractors ─────────────────────────────────────────────────────────

def _pan_number(text: str) -> Optional[str]:
    for word in text.upper().split():
        cand = re.sub(r'[^A-Z0-9]', '', word)
        if len(cand) >= 10:
            cand = cand[:10]
            letters = cand[:5].replace('0', 'O').replace('1', 'I').replace('8', 'B').replace('5', 'S')
            numbers = cand[5:9].replace('O', '0').replace('I', '1').replace('S', '5').replace('Z', '2').replace('B', '8')
            last_letter = cand[9].replace('0', 'O').replace('1', 'I').replace('5', 'S')
            pan = letters + numbers + last_letter
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
                return pan
    
    match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text.upper())
    return match.group(1) if match else None


def _dob(text: str) -> Optional[str]:
    m = re.search(r'(\d{2})[/\-1Ili\s\.]+([01]?\d)[/\-1Ili\s\.]+(\d{4})', text)
    if m:
        return f"{m.group(1)}/{m.group(2).zfill(2)}/{m.group(3)}"
    return None


def _name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if "GOV" in line.upper() or "INDIA" in line.upper() or "TAX" in line.upper() or "DEPART" in line.upper():
            if i + 1 < len(lines):
                cand = re.sub(r'[a-z].*$', '', lines[i+1]).strip(' /\\-')
                if cand:
                    return cand.title()
    return None


def _father_name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if "GOV" in line.upper() or "INDIA" in line.upper() or "TAX" in line.upper() or "DEPART" in line.upper():
            if i + 2 < len(lines):
                cand = re.sub(r'[a-z].*$', '', lines[i+2]).strip(' /\\-')
                if cand:
                    return cand.title()
    return None


def _name_fallback(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.fullmatch(r'(?i)name\s*:?', line.strip()):
            if i + 1 < len(lines):
                candidate = lines[i + 1]
                if _looks_like_name(candidate):
                    return candidate.title()
    for line in lines:
        if re.match(r'^[A-Z][A-Z\s\.]{4,}$', line) and len(line.split()) >= 2:
            return line.title()
    return None


def _father_name_fallback(lines: List[str]) -> Optional[str]:
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
