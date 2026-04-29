import re
from typing import Optional, List, Any

def extract_dl(text: str, detailed: List[Any] = None) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    name = None
    if detailed:
        name = _name_spatial(detailed)

    if not name: name = _name(lines)

    return {
        "dl_number": _dl_number(text),
        "name": name,
        "dob": _dob(text),
    }

def _dl_number(text: str) -> Optional[str]:
    clean_text = text.replace(' ', '').replace('-', '')
    m = re.search(r'\b([A-Z]{2}[0-9]{13})\b', clean_text)
    if m: return m.group(1)
    m = re.search(r'([A-Z]{2}[0-9]{2}[\s-]?[0-9]{11})', text)
    return m.group(1).strip() if m else None

def _dob(text: str) -> Optional[str]:
    m = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    if not m:
        m = re.search(r'(\d{2}-\d{2}-\d{4})', text)
    return m.group(1) if m else None

def _name_spatial(detailed: List[Any]) -> Optional[str]:
    # Name is usually below or next to the 'Name' label
    for box, text, conf in detailed:
        if "NAME" in text.upper() and conf > 0.3:
            label_right = box[1][0]
            label_bottom = box[2][1]
            for box2, text2, conf2 in detailed:
                if box2[0][1] > label_bottom and box2[0][1] < label_bottom + 100:
                    if len(text2.split()) >= 2:
                        return text2.strip().title()
    return None

def _name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'\bNAME\b', line, re.I):
            parts = re.split(r'[:\-]', line)
            if len(parts) > 1 and len(parts[-1].strip()) > 3:
                return parts[-1].strip().title()
    return None
