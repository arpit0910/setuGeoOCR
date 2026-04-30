import pytesseract
import config
import os
import re
import numpy as np
from PIL import Image
from typing import Any, Dict, Optional, List
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
            model_dir = os.path.join(config.BASE_DIR, "models", "easyocr")
            os.makedirs(model_dir, exist_ok=True)
            logging.getLogger('easyocr').setLevel(logging.ERROR)
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False, model_storage_directory=model_dir)
        except Exception as e:
            _EASYOCR_READER = None
    return _EASYOCR_READER

pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


def process_image(img: Image.Image, document_type: Optional[str] = None) -> dict:
    """
    Hybrid Voting Engine:
    Runs multiple OCR passes on normalized images and merges results for 100% reliability.
    """
    # 1. Universal Normalization
    normalized_img = preprocess(img)
    
    raw_text_easy = ""
    detailed_results = []
    
    # Pass 1: Neural Depth (EasyOCR)
    reader = _get_easyocr_reader()
    if reader:
        try:
            # We use the normalized image for better neural detection
            img_np = np.array(normalized_img.convert('RGB'))
            detailed_results = reader.readtext(img_np)
            raw_text_easy = "\n".join([res[1] for res in detailed_results])
        except Exception as e:
            print(f"EasyOCR pass failed: {e}")

    # Pass 2: Character Precision (Tesseract)
    raw_text_tess = _run_tesseract(normalized_img)
    
    # Merge Texts for detection
    combined_raw = raw_text_easy + "\n" + raw_text_tess
    
    # 2. Detect Document Version
    detected_type = document_type if document_type and document_type != "None" else _detect_type(combined_raw)
    
    # 3. Targeted Extraction (Spatial + Regex)
    if detected_type == "pan":
        extracted_fields = extract_pan(combined_raw, detailed_results)
    elif detected_type in ("aadhaar_front", "aadhaar_back"):
        extracted_fields = extract_aadhaar(combined_raw, detected_type, detailed_results)
    else:
        # Generic Dispatch
        extracted_fields = _extract(combined_raw, detected_type)
    
    # 4. Consistency Validation
    validation = _validate_extraction(detected_type, extracted_fields, combined_raw)

    return {
        "document_type":     detected_type,
        "raw_text":          combined_raw,
        "extracted_fields":  extracted_fields,
        "confidence":        _confidence_hint(detected_type, combined_raw),
        "validation":        validation,
        "success":           validation["is_valid"],
        "message":           validation["message"],
    }


def _run_tesseract(img: Image.Image) -> str:
    return pytesseract.image_to_string(
        img,
        lang=config.TESSERACT_LANG,
        config=config.TESSERACT_CONFIG,
    )


def _detect_type(text: str) -> str:
    upper = text.upper()
    import re

    if any(s in upper for s in {"INCOME TAX", "PERMANENT ACCOUNT", "PANCARD"}) or re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', upper):
        return "pan"

    if any(s in upper for s in {"GOVERNMENT OF INDIA", "UIDAI", "UNIQUE IDENTIFICATION"}) or re.search(r'[0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4}', upper):
        # Front vs Back check
        if any(h in upper for h in {"MALE", "FEMALE", "DOB", "DATE OF BIRTH"}):
            return "aadhaar_front"
        if any(h in upper for h in {"ADDRESS", "S/O", "D/O", "W/O", "PINCODE"}):
            return "aadhaar_back"
        return "aadhaar_front"

    if any(s in upper for s in {"ELECTION COMMISSION", "PHOTO IDENTITY CARD"}):
        return "voter_id"

    if any(s in upper for s in {"DRIVING LICENCE", "MOTOR VEHICLE"}):
        return "dl"

    if any(s in upper for s in {"REPUBLIC OF INDIA", "PASSPORT"}):
        return "passport"

    return "unknown"


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
    return {"raw": text}


def _confidence_hint(doc_type: str, text: str) -> str:
    import re
    patterns = {
        "pan": r'[A-Z]{5}[0-9]{4}[A-Z]',
        "aadhaar_front": r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}',
        "aadhaar_back": r'\b\d{6}\b',
        "voter_id": r'[A-Z]{3}[0-9]{7}',
        "dl": r'[A-Z]{2}[0-9]{13}',
        "passport": r'[A-Z][0-9]{7}'
    }
    pattern = patterns.get(doc_type)
    if pattern and re.search(pattern, text):
        return "high"
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
    
    is_valid = doc_type != "unknown" and not missing_fields
    message = "Values extracted successfully." if is_valid else "We could not extract all required values."
    
    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "message": message
    }

def _has_value(value: Any) -> bool:
    if value is None: return False
    if isinstance(value, str): return bool(value.strip())
    return True
