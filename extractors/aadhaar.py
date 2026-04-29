import re
from typing import Optional, List, Any


def extract_aadhaar(text: str, side: str, detailed: List[Any] = None) -> dict:
    if side == "aadhaar_front":
        return _extract_front(text, detailed)
    if side == "aadhaar_back":
        return _extract_back(text, detailed)
    return {}


# ── front ────────────────────────────────────────────────────────────────────

def _extract_front(text: str, detailed: List[Any] = None) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # 1. Name Spatial
    name = None
    if detailed:
        # Aadhaar names are usually above the DOB/Gender block
        name = _name_spatial_front(detailed)
    
    if not name:
        name = _name_front(lines)
        
    return {
        "aadhaar_number": _aadhaar_number(text),
        "name":           name,
        "dob":            _dob(text),
        "gender":         _gender(text),
        "year_of_birth":  _year_of_birth(text),
    }


def _name_spatial_front(detailed: List[Any]) -> Optional[str]:
    """
    Finds the name on Aadhaar front. Usually the first bold-ish 
    text block below the Government header.
    """
    # Find DOB box to use as anchor (name is usually above it)
    dob_box = None
    for box, text, conf in detailed:
        if any(kw in text.upper() for kw in ["DOB", "DATE OF BIRTH", "YEAR OF BIRTH", "YOB"]):
            dob_box = box
            break
            
    if dob_box:
        dob_top = dob_box[0][1]
        # Look for text boxes above DOB
        candidates = []
        for box, text, conf in detailed:
            box_bottom = box[2][1]
            if dob_top - 200 < box_bottom < dob_top:
                if _is_likely_name(text):
                    candidates.append((box_bottom, text))
        
        if candidates:
            # Pick the one closest to DOB
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1].strip().title()
            
    return None


# ── back ─────────────────────────────────────────────────────────────────────

def _extract_back(text: str, detailed: List[Any] = None) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    address = None
    if detailed:
        address = _address_spatial(detailed)
        
    if not address:
        address = _address(lines)
        
    return {
        "aadhaar_number": _aadhaar_number(text),
        "address":        address,
        "pincode":        _pincode(text),
    }


def _address_spatial(detailed: List[Any]) -> Optional[str]:
    """
    Finds address block starting from 'Address:' or 'S/O' labels.
    """
    start_y = None
    for box, text, conf in detailed:
        upper = text.upper()
        if any(kw in upper for kw in ["ADDRESS", "S/O", "D/O", "W/O", "C/O"]):
            start_y = box[0][1]
            break
            
    if start_y is not None:
        addr_parts = []
        for box, text, conf in detailed:
            box_top = box[0][1]
            # Capture everything below the trigger within a reasonable window
            if start_y - 20 <= box_top < start_y + 800:
                if len(text) > 2 and not re.search(r'\d{12}', text.replace(" ", "")):
                    # Clean the 'Address:' label from the first part if present
                    clean_text = re.sub(r'^(ADDRESS|ADDR|ADD)\s*[:\-]\s*', '', text, flags=re.I).strip()
                    addr_parts.append(clean_text)
        
        if addr_parts:
            return ", ".join(addr_parts)
            
    return None


# ── shared field extractors ──────────────────────────────────────────────────

def _aadhaar_number(text: str) -> Optional[str]:
    # 12-digit number, often formatted as XXXX XXXX XXXX
    clean_text = re.sub(r'[^0-9]', '', text)
    matches = re.findall(r'\d{12}', clean_text)
    if matches:
        return matches[-1] # Usually at the bottom
    return None


def _dob(text: str) -> Optional[str]:
    m = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    if not m:
        m = re.search(r'(\d{2}-\d{2}-\d{4})', text)
    return m.group(1) if m else None


def _year_of_birth(text: str) -> Optional[str]:
    m = re.search(r'(?:YOB|Year of Birth|Birth)\s*[:\-]?\s*(\d{4})', text, re.IGNORECASE)
    if not m:
        m = re.search(r'\b(19\d{2}|20[012]\d)\b', text)
    return m.group(1) if m else None


def _gender(text: str) -> Optional[str]:
    upper = text.upper()
    if "FEMALE" in upper: return "Female"
    if "MALE" in upper: return "Male"
    return None


def _is_likely_name(text: str) -> bool:
    _SKIP = {"GOVERNMENT", "INDIA", "UIDAI", "UNIQUE", "AUTHORITY", "MALE", "FEMALE", "DOB", "DATE", "BIRTH"}
    clean = re.sub(r'[^A-Za-z\s]', '', text).strip()
    words = clean.split()
    if not (2 <= len(words) <= 5): return False
    if any(w.upper() in _SKIP for w in words): return False
    return True


def _name_front(lines: List[str]) -> Optional[str]:
    for line in lines:
        if _is_likely_name(line):
            return line.strip().title()
    return None


def _address(lines: List[str]) -> Optional[str]:
    _TRIGGERS = {"S/O", "D/O", "W/O", "C/O", "ADDRESS", "ADDR:"}
    collecting = False
    addr_lines = []
    for line in lines:
        if any(t in line.upper() for t in _TRIGGERS): collecting = True
        if collecting:
            if not re.search(r'\d{12}', line.replace(" ", "")):
                addr_lines.append(line)
            if re.search(r'\b\d{6}\b', line): break
    return ", ".join(addr_lines) if addr_lines else None


def _pincode(text: str) -> Optional[str]:
    m = re.search(r'\b(\d{6})\b', text)
    return m.group(1) if m else None
