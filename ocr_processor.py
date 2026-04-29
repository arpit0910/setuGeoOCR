import pytesseract
import config
import os
import re
import numpy as np
from PIL import Image
from typing import Any, Dict, Optional
from utils.image_utils import preprocess
from extractors.pan import extract_pan
from extractors.aadhaar import extract_aadhaar

# OCR Engine State
_EASYOCR_READER = None

def _get_easyocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        try:
            import easyocr
            import logging
            # Set a persistent model storage directory in the project
            model_dir = os.path.join(config.BASE_DIR, "models", "easyocr")
            os.makedirs(model_dir, exist_ok=True)
            
            logging.getLogger('easyocr').setLevel(logging.ERROR)
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False, model_storage_directory=model_dir)
        except Exception as e:
            _EASYOCR_READER = None
    return _EASYOCR_READER

# Point pytesseract at the Tesseract binary
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


# ── public API ───────────────────────────────────────────────────────────────

def process_image(img: Image.Image, document_type: Optional[str] = None) -> dict:
    """
    Primary: Deep Learning (EasyOCR) with Spatial Awareness.
    Secondary: Tesseract (Fallback).
    """
    raw_text = ""
    detailed_results = []
    
    # 1. Try EasyOCR (Deep Learning)
    reader = _get_easyocr_reader()
    if reader:
        try:
            import numpy as np
            img_rgb = np.array(img.convert('RGB'))
            # Get boxes + text + confidence
            detailed_results = reader.readtext(img_rgb)
            raw_text = "\n".join([res[1] for res in detailed_results])
        except Exception as e:
            print(f"EasyOCR failed: {e}")

    # 2. Fallback to Tesseract if EasyOCR missed everything
    if not raw_text.strip():
        processed = preprocess(img)
        raw_text = _run_tesseract(processed)

    detected_type = document_type if document_type and document_type != "None" else _detect_type(raw_text)
    
    # 3. Extract with spatial awareness if available
    if detected_type == "pan":
        extracted_fields = extract_pan(raw_text, detailed_results)
    elif detected_type in ("aadhaar_front", "aadhaar_back"):
        extracted_fields = extract_aadhaar(raw_text, detected_type, detailed_results)
    elif detected_type == "voter_id":
        from extractors.voter_id import extract_voter_id
        extracted_fields = extract_voter_id(raw_text, detailed_results)
    elif detected_type == "dl":
        from extractors.dl import extract_dl
        extracted_fields = extract_dl(raw_text, detailed_results)
    elif detected_type == "passport":
        from extractors.passport import extract_passport
        extracted_fields = extract_passport(raw_text, detailed_results)
    else:
        extracted_fields = _extract(raw_text, detected_type)
    
    validation = _validate_extraction(detected_type, extracted_fields, raw_text)

    return {
        "document_type":     detected_type,
        "raw_text":          raw_text,
        "extracted_fields":  extracted_fields,
        "confidence":        _confidence_hint(detected_type, raw_text),
        "validation":        validation,
        "success":           validation["is_valid"],
        "message":           validation["message"],
    }


# ── OCR ──────────────────────────────────────────────────────────────────────

def _run_tesseract_detailed(img: Image.Image) -> dict:
    """
    Runs Tesseract in data mode to get coordinates and confidence for each word.
    """
    import pytesseract
    data = pytesseract.image_to_data(
        img,
        lang=config.TESSERACT_LANG,
        config=config.TESSERACT_CONFIG,
        output_type=pytesseract.Output.DICT
    )
    
    # Reconstruct lines based on block/line numbers
    lines = {}
    for i in range(len(data['text'])):
        if int(data['conf']) > 10:  # Ignore very low confidence noise
            line_id = f"{data['block_num'][i]}_{data['line_num'][i]}"
            if line_id not in lines:
                lines[line_id] = []
            lines[line_id].append(data['text'][i])
    
    full_text = "\n".join([" ".join(words) for words in lines.values()])
    return {
        "text": full_text,
        "data": data
    }

def _run_tesseract(img: Image.Image) -> str:
    # Basic fallback to string mode
    return pytesseract.image_to_string(
        img,
        lang=config.TESSERACT_LANG,
        config=config.TESSERACT_CONFIG,
    )


# ── document-type detection ──────────────────────────────────────────────────

_PAN_SIGNALS      = {"INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "INCOME TAX DEPT", "INCOMETAMDEPARIMENT"}
_AADHAAR_SIGNALS  = {"GOVERNMENT OF INDIA", "UIDAI", "UNIQUE IDENTIFICATION", "GOUERNMENT OF INDIA"}
_VOTER_SIGNALS    = {"ELECTION COMMISSION", "ELECTOR PHOTO IDENTITY CARD", "ELECTOR'S PHOTO IDENTITY CARD"}
_DL_SIGNALS       = {"DRIVING LICENCE", "DRIVING LICENSE", "MOTOR VEHICLE", "UNION OF INDIA"}
_PASSPORT_SIGNALS = {"REPUBLIC OF INDIA", "PASSPORT", "REPUBLIQUE DE L'INDE"}

_AADHAAR_FRONT_HINTS = {"MALE", "FEMALE", "TRANSGENDER", "DOB", "DATE OF BIRTH", "YOB", "YEAR OF BIRTH"}
_AADHAAR_BACK_HINTS  = {"S/O", "D/O", "W/O", "C/O", "VILLAGE", "DISTRICT", "ADDRESS", "PINCODE"}


def _detect_type(text: str) -> str:
    upper = text.upper()
    import re

    # High-confidence signals
    # PAN Card: 5 letters, 4 digits, 1 letter
    if any(s in upper for s in _PAN_SIGNALS) or re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', upper, re.I):
        return "pan"

    if any(s in upper for s in _VOTER_SIGNALS):
        return "voter_id"

    if any(s in upper for s in _PASSPORT_SIGNALS):
        return "passport"

    if any(s in upper for s in _DL_SIGNALS) or ("DL" in upper and "DOB" in upper and "ISSUE" in upper):
        return "dl"

    # Aadhaar detection (Front/Back)
    # Aadhaar: 12 digits (often with spaces/dashes)
    is_aadhaar = any(s in upper for s in _AADHAAR_SIGNALS) or re.search(r'[0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4}', upper)
    
    if is_aadhaar:
        front_score = sum(1 for h in _AADHAAR_FRONT_HINTS if h in upper)
        back_score  = sum(1 for h in _AADHAAR_BACK_HINTS  if h in upper)
        
        # If it has address indicators, it's likely back
        if any(h in upper for h in ["ADDRESS", "VILLAGE", "DISTRICT", "PINCODE", "S/O", "D/O", "W/O"]):
            back_score += 2
            
        return "aadhaar_front" if front_score >= back_score else "aadhaar_back"

    # Fallback heuristics if signals missed
    if "ADDRESS:" in upper or "FATHER:" in upper or "W/O" in upper or "S/O" in upper or "C/O" in upper:
        return "aadhaar_back"  # Common for cropped aadhaar back

    return "unknown"


# ── field extraction dispatch ────────────────────────────────────────────────

def _extract(text: str, doc_type: str) -> dict:
    if doc_type == "pan":
        return extract_pan(text)
    if doc_type in ("aadhaar_front", "aadhaar_back"):
        return extract_aadhaar(text, doc_type)
    if doc_type == "voter_id":
        from extractors.voter_id import extract_voter_id
        return extract_voter_id(text)
    if doc_type == "dl":
        from extractors.dl import extract_dl
        return extract_dl(text)
    if doc_type == "passport":
        from extractors.passport import extract_passport
        return extract_passport(text)
    return {"raw": text}  # unknown — return raw text so caller can inspect


# ── confidence hint ──────────────────────────────────────────────────────────

def _confidence_hint(doc_type: str, text: str) -> str:
    """
    Simple heuristic: if the key identifier was found we mark confidence as 'high', otherwise 'low'.
    """
    import re
    if doc_type == "pan":
        return "high" if re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text) else "low"
    if doc_type in ("aadhaar_front", "aadhaar_back"):
        return "high" if re.search(r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}', text) else "low"
    if doc_type == "voter_id":
        return "high" if re.search(r'[A-Z]{3}[0-9]{7}', text) else "low"
    if doc_type == "dl":
        return "high" if re.search(r'[A-Z]{2}[0-9]{13}', text) or re.search(r'[A-Z]{2}[0-9]{2}[\s-]?[0-9]{11}', text) else "low"
    if doc_type == "passport":
        return "high" if re.search(r'[A-Z][0-9]{7}', text) else "low"
    return "low"


_REQUIRED_FIELDS = {
    "pan": ["pan_number", "name", "father_name", "dob"],
    "aadhaar_front": ["aadhaar_number", "name"],
    "aadhaar_back": ["address"],
    "voter_id": ["voter_id_number", "name"],
    "dl": ["dl_number", "name", "dob"],
    "passport": ["passport_number", "surname", "given_names"],
}


def _validate_extraction(doc_type: str, fields: Dict[str, Any], raw_text: str) -> dict:
    required_fields = _REQUIRED_FIELDS.get(doc_type, [])
    missing_fields = [field for field in required_fields if not _has_value(fields.get(field))]

    if doc_type == "aadhaar_front":
        has_birth_value = _has_value(fields.get("dob")) or _has_value(fields.get("year_of_birth"))
        if not has_birth_value:
            missing_fields.append("dob_or_year_of_birth")

    raw_text_length = len(raw_text.strip())
    is_valid = doc_type != "unknown" and not missing_fields and raw_text_length >= 20

    if is_valid:
        message = "Values extracted successfully."
    elif doc_type == "unknown":
        message = "We could not identify the document type. Please upload a clearer image."
    else:
        message = (
            "We could not extract all required values. "
            "Please upload a clearer, properly aligned image. The current image may be blurry or incomplete."
        )

    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "required_fields": required_fields,
        "raw_text_length": raw_text_length,
        "message": message,
    }


def _has_value(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return True
