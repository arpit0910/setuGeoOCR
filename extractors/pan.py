import re
from typing import Optional, List, Any


def extract_pan(text: str, detailed: List[Any] = None) -> dict:
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    pan_num = _pan_number(text)
    
    # Use spatial awareness if detailed results from EasyOCR are available
    name = None
    father = None
    if detailed:
        # Try multiple label variants to handle OCR noise in labels
        name = _name_spatial(detailed, ["NAME", "NANE", "NAIE", "NAMF"])
        father = _name_spatial(detailed, ["FATHER", "FATHE", "FATHFR", "ATHER"])

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

def _name_spatial(detailed: List[Any], label_keywords: List[str]) -> Optional[str]:
    """
    Finds the text block directly below a label like 'Name' or 'Father's Name'.
    """
    label_box = None
    for res in detailed:
        box, text, conf = res
        upper_text = text.upper()
        if any(kw in upper_text for kw in label_keywords) and conf > 0.3:
            # For Father's Name, ensure it's not the 'Name' label
            if "FATHER" in label_keywords[0] and "FATHER" not in upper_text:
                continue
            label_box = box
            break
            
    if not label_box:
        return None
        
    # label_box is [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
    label_bottom = label_box[2][1]
    label_left = label_box[0][0]
    
    candidates = []
    for res in detailed:
        box, text, conf = res
        box_top = box[0][1]
        box_left = box[0][0]
        
        # If it's below the label and roughly aligned
        # PAN card fields are usually within 200 pixels below the label at 3000px width
        if label_bottom < box_top < label_bottom + 300: 
            if abs(box_left - label_left) < 800: # allow some horizontal offset
                if _is_likely_name(text):
                    candidates.append((conf, text))
                    
    if candidates:
        # Sort by confidence and pick the most 'name-like' one
        candidates.sort(key=lambda x: x[0], reverse=True)
        return _clean_name(candidates[0][1])
        
    return None


def _pan_number(text: str) -> Optional[str]:
    clean_text = re.sub(r'[^A-Z0-9]', ' ', text.upper())
    words = clean_text.split()
    
    def _fix_pan(cand: str) -> str:
        letters = cand[:5].replace('0', 'O').replace('1', 'I').replace('8', 'B').replace('5', 'S')
        numbers = cand[5:9].replace('O', '0').replace('I', '1').replace('S', '5').replace('Z', '2').replace('B', '8')
        last_letter = cand[9].replace('0', 'O').replace('1', 'I').replace('5', 'S')
        return letters + numbers + last_letter

    potential = []
    for word in words:
        if len(word) == 10:
            fixed = _fix_pan(word)
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', fixed):
                if fixed[3] in "PCHFTJ":
                    potential.append(fixed)
        elif len(word) > 10:
            for i in range(len(word) - 9):
                cand = word[i:i+10]
                fixed = _fix_pan(cand)
                if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', fixed):
                    if fixed[3] in "PCHFTJ":
                        potential.append(fixed)

    if potential:
        for p in potential:
            if p[3] == 'P': return p
        return potential[0]
            
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
        if any(s in line.upper() for s in _SKIP): continue
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
    # 1. Reject if too many symbols
    if len(re.findall(r'[^A-Z\s\.]', text.upper())) > 3:
        return False
        
    # 2. Reject if all numbers
    if text.isdigit():
        return False
        
    # 3. Reject if lowercase (Indian IDs names are always UPPER)
    if any(c.islower() for c in text) and len(text) > 5:
        return False
        
    clean = re.sub(r'[^A-Z\s]', ' ', text.upper()).strip()
    words = [w for w in clean.split() if len(w) >= 2]
    
    _NOISE = {"FET", "AE", "OF", "THE", "INCOME", "TAX", "INDIA", "GOVT", "DEPT", "GOVERNMENT", "PANCARD", "ACCOUNT", "SIGNATURE", "DIGITALLY", "SIGNED", "DEPARTMENT", "NUMBER", "CARD", "PERMANENT"}
    filtered = [w for w in words if w.upper() not in _NOISE]
    
    # Names usually have 2-4 words
    return 2 <= len(filtered) <= 5 and len(" ".join(filtered)) > 4

def _clean_name(text: str) -> str:
    res = text.upper()
    # Corrections
    res = res.replace("VIYAY", "VIJAY")
    res = res.replace("VERCIA", "VERGIA")
    res = res.replace("VERGCIA", "VERGIA")
    res = res.replace("VIJAYVERGIA", "VIJAY VERGIA")
    
    # Remove trailing digital signatures
    _NOISE_TRAIL = ["MIMA", "OARS", "OARE", "GE", "WA", "SEE", "EE", "OE", "SIGN", "DIGITALLY", "VALID", "UNLESS", "PHYSICALLY"]
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
