import re
from typing import Optional, List, Any

def extract_voter_id(text: str, detailed: List[Any] = None) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    name = None
    father = None
    if detailed:
        name = _name_spatial(detailed, ["NAME", "ELECTOR", "NAME"])
        father = _name_spatial(detailed, ["FATHER", "HUSBAND", "NAME"])

    if not name: name = _name(lines)
    if not father: father = _father_name(lines)

    return {
        "voter_id_number": _voter_id_number(text),
        "name": name,
        "father_name": father,
        "dob": _dob(text),
    }

def _voter_id_number(text: str) -> Optional[str]:
    m = re.search(r'\b([A-Z]{3}[0-9]{7})\b', text)
    if not m:
        # Sometimes 10 characters but different format
        m = re.search(r'\b([A-Z0-9]{10})\b', text)
    return m.group(1) if m else None

def _dob(text: str) -> Optional[str]:
    m = re.search(r'(?:DOB|Birth|Age)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})', text, re.IGNORECASE)
    return m.group(1) if m else None

def _name_spatial(detailed: List[Any], keywords: List[str]) -> Optional[str]:
    label_box = None
    for box, text, conf in detailed:
        if any(kw in text.upper() for kw in keywords) and conf > 0.3:
            label_box = box
            break
            
    if label_box:
        label_right = label_box[1][0]
        label_top = label_box[0][1]
        # Voter ID names are often to the RIGHT of the label
        for box, text, conf in detailed:
            box_left = box[0][0]
            box_top = box[0][1]
            if label_right < box_left < label_right + 500:
                if abs(box_top - label_top) < 50:
                    if len(text.split()) >= 2:
                        return text.strip().title()
    return None

def _name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'NAME', line, re.I):
            parts = re.split(r'[:\-]', line)
            if len(parts) > 1 and len(parts[-1].strip()) > 3:
                return parts[-1].strip().title()
    return None

def _father_name(lines: List[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if re.search(r'FATHER|HUSBAND', line, re.I):
            parts = re.split(r'[:\-]', line)
            if len(parts) > 1 and len(parts[-1].strip()) > 3:
                return parts[-1].strip().title()
    return None
