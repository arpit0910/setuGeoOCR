import io
import os
import logging
import time
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Security, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from starlette.status import HTTP_403_FORBIDDEN

import config
from ocr_processor import process_image

# ── logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ocr_service.log")
    ]
)
logger = logging.getLogger("setu-geo-ocr")

# ── app initialization ────────────────────────────────────────────────────────

app = FastAPI(
    debug=True,
    title="SetuGeo OCR Service",
    description="Production-ready OCR microservice for Laravel integration.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://geosetu.com",
        "https://www.geosetu.com",
        "https://api.geosetu.com",
        "http://localhost",  # For local development
        "http://127.0.0.1"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── security ──────────────────────────────────────────────────────────────────

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == config.API_KEY:
        return api_key
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )

# ── middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Path: {request.url.path} | Method: {request.method} | Duration: {process_time:.4f}s")
    return response

# ── exception handlers ────────────────────────────────────────────────────────

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "status": "online",
                "error": "Not Found",
                "message": "The SetuGeo OCR service is live, but the URL you are trying to access does not exist.",
                "requested_path": request.url.path,
                "docs_url": "/docs"
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# ── root & health ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, tags=["System"])
def root():
    """Root endpoint returning the testing UI."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Welcome to SetuGeo OCR.</h1><p>API is running.</p>"

@app.get("/health", tags=["System"])
def health():
    """Health check endpoint for monitoring."""
    import pytesseract
    tesseract_version = "unknown"
    try:
        tesseract_version = pytesseract.get_tesseract_version().version
    except Exception:
        pass
    
    return {
        "status": "ok",
        "service": "SetuGeo OCR Service",
        "version": "1.0.0",
        "tesseract": tesseract_version,
        "timestamp": time.time()
    }

# ── main OCR endpoint ─────────────────────────────────────────────────────────

@app.post("/ocr/extract", tags=["OCR"], dependencies=[Depends(get_api_key)])
async def extract(
    image: UploadFile = File(..., description="Image of the document (JPEG, PNG, WEBP, BMP, TIFF)"),
    document_type: Optional[str] = Form(
        None,
        description="Optional hint: 'pan' | 'aadhaar_front' | 'aadhaar_back' | 'voter_id' | 'dl' | 'passport'. "
                    "If omitted the service auto-detects.",
    ),
):
    """
    Extract data from a document image.
    Requires X-API-KEY header for authentication.
    """
    logger.info(f"Received OCR request. Filename: {image.filename}, Type: {document_type}")
    
    _validate_file(image, document_type)

    try:
        contents = await image.read()
    except Exception as e:
        logger.error(f"Failed to read upload: {str(e)}")
        raise HTTPException(status_code=400, detail="Could not read the uploaded image.")

    try:
        img = Image.open(io.BytesIO(contents))
        # Ensure we can actually read the image data
        img.verify()
        # Re-open after verify as verify() ruins the object for further use
        img = Image.open(io.BytesIO(contents))
    except Exception as e:
        logger.error(f"Invalid image format: {str(e)}")
        raise HTTPException(status_code=422, detail="Invalid image format or corrupt file.")

    try:
        result = process_image(img, document_type or None)
        logger.info(f"Successfully processed {detected_type_info(result)}")
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("OCR Processing Error")
        raise HTTPException(status_code=500, detail=f"OCR engine error: {str(e)}")

def detected_type_info(result):
    return result.get("document_type", "unknown")

# ── validation ────────────────────────────────────────────────────────────────

_VALID_DOC_TYPES = {"pan", "aadhaar_front", "aadhaar_back", "voter_id", "dl", "passport", None}

def _validate_file(file: UploadFile, document_type: Optional[str]):
    if file.content_type not in config.ALLOWED_EXTENSIONS:
        logger.warning(f"Unsupported content type: {file.content_type}")
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}",
        )

    if document_type and document_type not in _VALID_DOC_TYPES:
        logger.warning(f"Invalid document type requested: {document_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{document_type}'. "
                   f"Allowed values: pan, aadhaar_front, aadhaar_back, voter_id, dl, passport",
        )

# ── entry point ───────────────────────────────────────────────────────────────

# This is the Entry Point callable that most hosting provides look for
# If your host supports ASGI: main:app
# If your host supports WSGI: main:wsgi_app
from a2wsgi import ASGIMiddleware
wsgi_app = ASGIMiddleware(app)

if __name__ == "__main__":
    import uvicorn
    # Use config values, default reload to False in prod but here we check for env
    is_dev = os.getenv("ENV", "production").lower() == "development"
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=is_dev)
