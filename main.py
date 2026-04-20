import io
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

import config
from ocr_processor import process_image

app = FastAPI(
    title="SetuGeo OCR Service",
    description="Extracts structured fields from PAN cards, Aadhaar cards (front/back), and other documents.",
    version="1.0.0",
)


# ── health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "SetuGeo OCR Service", "version": "1.0.0"}


# ── main OCR endpoint ─────────────────────────────────────────────────────────

@app.post("/ocr/extract")
async def extract(
    image: UploadFile = File(..., description="Image of the document (JPEG, PNG, WEBP, BMP, TIFF)"),
    document_type: Optional[str] = Form(
        None,
        description="Optional hint: 'pan' | 'aadhaar_front' | 'aadhaar_back'. "
                    "If omitted the service auto-detects.",
    ),
):
    _validate_file(image, document_type)

    contents = await image.read()

    try:
        img = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=422, detail="Could not decode the uploaded image.")

    result = process_image(img, document_type or None)
    return JSONResponse(content=result)


# ── validation ────────────────────────────────────────────────────────────────

_VALID_DOC_TYPES = {"pan", "aadhaar_front", "aadhaar_back", None}


def _validate_file(file: UploadFile, document_type: Optional[str]):
    if file.content_type not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}",
        )

    if document_type and document_type not in _VALID_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{document_type}'. "
                   f"Allowed values: pan, aadhaar_front, aadhaar_back",
        )


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
