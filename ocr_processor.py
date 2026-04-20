import pytesseract
from PIL import Image

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

    return {
        "document_type":     detected_type,
        "raw_text":          raw_text,
        "extracted_fields":  _extract(raw_text, detected_type),
        "confidence":        _confidence_hint(detected_type, raw_text),
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
