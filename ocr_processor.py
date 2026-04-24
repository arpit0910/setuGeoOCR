import pytesseract
from PIL import Image
from typing import Any

import config
from utils.image_utils import preprocess
from extractors.pan import extract_pan
from extractors.aadhaar import extract_aadhaar

# Point pytesseract at the Tesseract binary
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


# ── public API ───────────────────────────────────────────────────────────────

def process_image(img: Image.Image, document_type: str | None = None) -> dict:
    """
    Main entry point.
    - Preprocesses the image for Tesseract.
    - Runs OCR.
    - Auto-detects document type if not provided.
    - Extracts structured fields.
    Returns a dict with document_type, raw_text, and extracted_fields.
    """
    processed = preprocess(img)
    raw_text  = _run_ocr(processed)

    detected_type = document_type or _detect_type(raw_text)
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

def _run_ocr(img: Image.Image) -> str:
    return pytesseract.image_to_string(
        img,
        lang=config.TESSERACT_LANG,
        config=config.TESSERACT_CONFIG,
    )


# ── document-type detection ──────────────────────────────────────────────────

_PAN_SIGNALS      = {"INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "INCOME TAX DEPT"}
_AADHAAR_SIGNALS  = {"GOVERNMENT OF INDIA", "UIDAI", "UNIQUE IDENTIFICATION"}

_AADHAAR_FRONT_HINTS = {"MALE", "FEMALE", "TRANSGENDER", "DOB", "DATE OF BIRTH", "YOB", "YEAR OF BIRTH"}
_AADHAAR_BACK_HINTS  = {"S/O", "D/O", "W/O", "C/O", "VILLAGE", "DISTRICT", "ADDRESS"}


def _detect_type(text: str) -> str:
    upper = text.upper()

    if any(s in upper for s in _PAN_SIGNALS):
        return "pan"

    if any(s in upper for s in _AADHAAR_SIGNALS):
        front_score = sum(1 for h in _AADHAAR_FRONT_HINTS if h in upper)
        back_score  = sum(1 for h in _AADHAAR_BACK_HINTS  if h in upper)
        return "aadhaar_front" if front_score >= back_score else "aadhaar_back"

    return "unknown"


# ── field extraction dispatch ────────────────────────────────────────────────

def _extract(text: str, doc_type: str) -> dict:
    if doc_type == "pan":
        return extract_pan(text)
    if doc_type in ("aadhaar_front", "aadhaar_back"):
        return extract_aadhaar(text, doc_type)
    return {"raw": text}  # unknown — return raw text so caller can inspect


# ── confidence hint ──────────────────────────────────────────────────────────

def _confidence_hint(doc_type: str, text: str) -> str:
    """
    Simple heuristic: if the key identifier (PAN number / Aadhaar number)
    was found we mark confidence as 'high', otherwise 'low'.
    """
    import re
    if doc_type == "pan":
        return "high" if re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text) else "low"
    if doc_type in ("aadhaar_front", "aadhaar_back"):
        return "high" if re.search(r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}', text) else "low"
    return "low"


_REQUIRED_FIELDS = {
    "pan": ["pan_number", "name", "father_name", "dob"],
    "aadhaar_front": ["aadhaar_number", "name"],
    "aadhaar_back": ["aadhaar_number", "address", "pincode"],
}


def _validate_extraction(doc_type: str, fields: dict[str, Any], raw_text: str) -> dict:
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
