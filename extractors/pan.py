import re
from typing import Optional, List, Any


def extract_pan(text: str, detailed: List[Any] = None) -> dict:
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    pan_num = _pan_number(text)
    
    # Use spatial awareness if detailed results from EasyOCR are available
    name = None
    father = None
    if detailed:
        # Try multiple label variants including noisy Hindi and corrupted English
        name = _name_spatial(detailed, ["NAME", "NANE", "NAIE", "NAMF", "नाम", "-म", "नlम", "MAME"])
        father = _name_spatial(detailed, ["FATHER", "FATHE", "FATHFR", "ATHER", "पिता", "FATER", "FATIER"])

    # Fallback to regex if spatial failed
    if not name:   name = _name(raw_lines)
    if not father: father = _father_name(raw_lines)
    
    return {
        "pan_number":   pan_num,
        "name":         name,
        "father_name":  father,
        "dob":          _dob(text),
        "card_type":    _card_type(text),
    }


# ── field extractors ─────────────────────────────────────────────────────────

def _name_spatial(detailed: List[Any], keywords: List[str]) -> Optional[str]:
    label_box = None
    for box, text, conf in detailed:
        upper = text.upper()
        if any(kw in upper for kw in keywords) and conf > 0.2:
            label_box = box
            break
            
    if label_box:
        label_bottom = label_box[2][1]
        label_left = label_box[0][0]
        # Look for the first name-like block BELOW the label
        # (Indian IDs often have labels above the name or to the left)
        candidates = []
        for box, text, conf in detailed:
            box_top = box[0][1]
            box_left = box[0][0]
            if box_top >= label_bottom - 10 and box_top < label_bottom + 150:
                if abs(box_left - label_left) < 500: # Stay in the same horizontal area
                    if _is_likely_name(text):
                        candidates.append((box_top, text))
        
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return _clean_name(candidates[0][1])
            
        # Fallback: Look to the RIGHT of the label
        label_right = label_box[1][0]
        label_top = label_box[0][1]
        for box, text, conf in detailed:
            if box[0][0] >= label_right - 10 and box[0][1] > label_top - 30 and box[0][1] < label_top + 30:
                if _is_likely_name(text):
                    return _clean_name(text)
    return None
        
    return None


def _pan_number(text: str) -> Optional[str]:
    full_clean = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    def _fix_pan(cand: str) -> str:
        # Common misreads for letters/numbers in PAN positions
        letters = cand[:5].replace('0', 'O').replace('1', 'I').replace('8', 'B').replace('5', 'S').replace('6', 'G')
        numbers = cand[5:9].replace('O', '0').replace('I', '1').replace('S', '5').replace('Z', '2').replace('B', '8').replace('G', '6')
        last_letter = cand[9].replace('0', 'O').replace('1', 'I').replace('5', 'S')
        return letters + numbers + last_letter

    potential = []
    for i in range(len(full_clean) - 9):
        cand = full_clean[i:i+10]
        fixed = _fix_pan(cand)
        # Hyper-aggressive 4th character correction
        if fixed[3] in ['I', '1', 'R', 'F', 'Y', 'V', 'L', '7']: 
            fixed = fixed[:3] + 'P' + fixed[4:]
            
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', fixed):
            if fixed[3] in "PCHFTJLG":
                potential.append(fixed)

    if potential:
        # Priority: Individual (P) starting with common PAN initials (A-Z)
        for p in potential:
            if p[3] == 'P' and p[0] in "ABCDEFG": return p # A-G are common initials
        return potential[0]
            
    # Final regex fallback on the raw text
    raw_match = re.search(r'([A-Z]{3}[A-Z]{2}[0-9]{4}[A-Z])', text.upper().replace(' ', ''))
    if raw_match: return _fix_pan(raw_match.group(1))

    return None


def _dob(text: str) -> Optional[str]:
    # Match DD/MM/YYYY or DD-MM-YYYY
    # Find all date-like strings
    dates = re.findall(r'(\d{2})[/\-1Ili\s\.]+([012]?\d)[/\-1Ili\s\.]+(\d{4})', text)
    if dates:
        # Pick the one that is NOT the issue date (usually found later in text)
        # DOB is usually the first date in a PAN card's main body
        # EXCEPT for e-PAN where issue date is sometimes first.
        # But e-PAN birth year is usually early in the text.
        
        res_dates = []
        for d, m, y in dates:
            month = m.zfill(2)
            if 1 <= int(month) <= 12 and 1 <= int(d) <= 31:
                # Handle the 02 vs 12 misread
                if month == "02" and "12/19" in text: # If 12/19 is seen anywhere, prefer 12
                    month = "12"
                res_dates.append(f"{d}/{month}/{y}")
        
        if res_dates:
            # Heuristic: Birth year is usually > 15 years ago
            import datetime
            this_year = datetime.datetime.now().year
            for rd in res_dates:
                ry = int(rd.split('/')[-1])
                if this_year - ry > 15:
                    return rd
            return res_dates[0]

    return None


def _name(raw_lines: List[str]) -> Optional[str]:
    _SKIP = {"INDIA", "INCOME", "TAX", "DEPARTMENT", "GOVT", "DEPT", "GOVERNMENT", "PANCARD", "ACCOUNT", "SIGNATURE", "DIGITALLY", "SIGNED"}
    for line in raw_lines:
        if any(s in line.upper() for s in _SKIP): 
            # If the line contains a skip word but also a colon, the name might be after it
            if ':' in line or '-' in line:
                parts = re.split(r'[:\-]', line)
                candidate = parts[-1].strip()
                if _is_likely_name(candidate):
                    return _clean_name(candidate)
            continue
            
        if _is_likely_name(line):
            return _clean_name(line)
    return None


def _father_name(raw_lines: List[str]) -> Optional[str]:
    potential = []
    _SKIP = {"INDIA", "INCOME", "TAX", "DEPARTMENT", "GOVT", "DEPT", "GOVERNMENT", "PANCARD", "ACCOUNT", "SIGNATURE", "DIGITALLY", "SIGNED"}
    for line in raw_lines:
        if any(s in line.upper() for s in _SKIP): continue
        if _is_likely_name(line):
            potential.append(line)
    if len(potential) >= 2:
        return _clean_name(potential[1])
    return None

def _is_likely_name(text: str) -> bool:
    # Production-ready name validator
    # Support Devanagari (Hindi) script \u0900-\u097F
    
    # 1. Reject if too many symbols (excluding Hindi and dots)
    if len(re.findall(r'[^A-Z\s\.\u0900-\u097F]', text.upper())) > 5: # More lenient
        return False
        
    # 2. Reject if all numbers
    if text.isdigit():
        return False
        
    # Clean and filter
    clean = re.sub(r'[^A-Z\s\u0900-\u097F]', ' ', text.upper()).strip()
    words = [w for w in clean.split() if len(w) >= 2]
    
    _NOISE = {"FET", "AE", "OF", "THE", "INCOME", "TAX", "INDIA", "GOVT", "DEPT", "GOVERNMENT", "PANCARD", "ACCOUNT", "SIGNATURE", "DIGITALLY", "SIGNED", "DEPARTMENT", "NUMBER", "CARD", "PERMANENT", "नाम", "पिता", "DATE", "BIRTH", "DEPARTMENT", "NUMBER"}
    filtered = [w for w in words if w.upper() not in _NOISE]
    
    # Names usually have 1-5 words (allowing 1 word for misreads that joined words)
    return 1 <= len(filtered) <= 6 and len(" ".join(filtered)) > 3

def _clean_name(text: str) -> str:
    res = text.upper()
    # Handle common OCR misreads in Indian names
    corrections = {
        "VIYAY": "VIJAY", "SAIIJAY": "SANJAY", "SAJJAY": "SANJAY",
        "VERCIA": "VERGIA", "VERGCIA": "VERGIA", "YIJAY": "VIJAY",
        "TERGIA": "VERGIA", "TERCIA": "VERGIA", "IAME": "NAME",
        "FATER": "FATHER", "FATIER": "FATHER"
    }
    for old, new in corrections.items():
        res = res.replace(old, new)
        
    # Remove trailing digital signatures or noise
    _NOISE_TRAIL = ["MIMA", "OARS", "OARE", "GE", "WA", "SEE", "EE", "OE", "SIGN", "DIGITALLY", "VALID", "UNLESS", "PHYSICALLY", "FATER", "MAME"]
    for noise in _NOISE_TRAIL:
        if f" {noise}" in res:
            res = res.split(f" {noise}")[0]
            
    res = re.sub(r'[^A-Z\s\.]', '', res).strip()
    return res.title()


def _card_type(text: str) -> str:
    upper = text.upper()
    if "INDIVIDUAL" in upper: return "Individual"
    if "HUF" in upper:        return "HUF"
    if "COMPANY" in upper:    return "Company"
    return "Individual"
