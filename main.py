import os
import io
import logging
import time
from typing import Optional

# 1. Environment & Thread Configuration (CRITICAL: MUST BE AT THE ABSOLUTE TOP)
# --------------------------------------------------------------------------
# Limit threads before any OCR-related libraries (cv2, numpy) are imported.
# This prevents "Resource temporarily unavailable" errors on shared hosting.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["CV_NUM_THREADS"] = "1"

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Security, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from PIL import Image
from starlette.status import HTTP_403_FORBIDDEN
from starlette.exceptions import HTTPException as StarletteHTTPException

# Define base directory for absolute pathing
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Logging Setup
# --------------------------------------------------------------------------
# Use an absolute path for the log file to ensure it's written in your project folder.
log_file_path = os.path.join(BASE_DIR, "ocr_service.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path)
    ]
)
logger = logging.getLogger("setu-geo-ocr")

# 3. App Initialization
# --------------------------------------------------------------------------
app = FastAPI(
    debug=True,
    title="SetuGeo OCR Service",
    description="Optimized OCR microservice for cPanel/CloudLinux.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://setugeo.com",
        "https://www.setugeo.com",
        "https://api.setugeo.com",
        "http://localhost",
        "http://127.0.0.1"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Security & Configuration
# --------------------------------------------------------------------------
try:
    import config
except ImportError:
    logger.error("config.py not found in the application root.")
    raise

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == config.API_KEY:
        return api_key
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )

# 5. Exception Handlers
# --------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "status": "online",
                "error": "Not Found",
                "message": "SetuGeo OCR is live. Endpoint not found.",
                "docs_url": "/docs"
            }
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# 6. Routes
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["System"])
async def root():
    """Root endpoint serving index.html."""
    logger.info("Root endpoint called")
    index_path = os.path.join(BASE_DIR, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error reading index.html: {e}")
        return HTMLResponse("<h1>SetuGeo OCR</h1><p>Service is running.</p>")

@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint for monitoring."""
    import pytesseract
    tesseract_version = "unknown"
    try:
        # Use run_in_threadpool for binary calls
        tesseract_version = await run_in_threadpool(pytesseract.get_tesseract_version)
        tesseract_version = tesseract_version.version
    except Exception:
        pass
    
    return {
        "status": "ok",
        "tesseract": tesseract_version,
        "timestamp": time.time()
    }

@app.post("/ocr/extract", tags=["OCR"], dependencies=[Depends(get_api_key)])
async def extract(
    image: UploadFile = File(..., description="Image of the document (JPEG, PNG, WEBP, BMP, TIFF)"),
    document_type: Optional[str] = Form(None),
):
    """
    Extract data from a document image.
    Uses run_in_threadpool to offload blocking OCR task to a separate thread.
    """
    # --- LAZY LOADING ---
    try:
        from ocr_processor import process_image
        # Additional OpenCV thread limit
        try:
            import cv2
            cv2.setNumThreads(0)
        except ImportError:
            pass
    except ImportError as e:
        logger.error(f"Failed to import ocr_processor: {e}")
        raise HTTPException(status_code=500, detail="OCR Engine failed to initialize.")

    logger.info(f"Received OCR request. Filename: {image.filename}, Type: {document_type}")
    
    _validate_file(image, document_type)

    try:
        contents = await image.read()
        
        img = Image.open(io.BytesIO(contents))
        # Use run_in_threadpool for the heavy part
        result = await run_in_threadpool(process_image, img, document_type or None)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("OCR Processing Error")
        raise HTTPException(status_code=500, detail=f"OCR engine error: {str(e)}")

# 7. Helper & Validation
# --------------------------------------------------------------------------
_VALID_DOC_TYPES = {"pan", "aadhaar_front", "aadhaar_back", "voter_id", "dl", "passport", None}

def _validate_file(file: UploadFile, document_type: Optional[str]):
    if file.content_type not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'."
        )
    if document_type and document_type not in _VALID_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid document_type.",
        )

# 8. Entry point for local testing
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)