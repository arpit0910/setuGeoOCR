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
from starlette.exceptions import HTTPException as StarletteHTTPException

# 1. Environment & Thread Configuration
# --------------------------------------------------------------------------
# CRITICAL: Limit threads before any OCR-related libraries are imported.
# This prevents "Resource temporarily unavailable" errors on shared hosting.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

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

# 5. Middleware & Exception Handlers
# --------------------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Path: {request.url.path} | Method: {request.method} | Duration: {process_time:.4f}s")
    return response

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
def root():
    """Root endpoint using an absolute path to index.html."""
    index_path = os.path.join(BASE_DIR, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>SetuGeo OCR</h1><p>Service is running. See <a href='/docs'>/docs</a></p>"

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
    Uses LAZY LOADING to prevent startup timeouts on shared hosting.
    """
    # --- LAZY LOADING ---
    # We import the heavy processor ONLY when this route is hit.
    try:
        from ocr_processor import process_image
    except ImportError as e:
        logger.error(f"Failed to import ocr_processor: {e}")
        raise HTTPException(status_code=500, detail="OCR Engine failed to initialize.")

    logger.info(f"Received OCR request. Filename: {image.filename}, Type: {document_type}")
    
    _validate_file(image, document_type)

    try:
        contents = await image.read()
        img = Image.open(io.BytesIO(contents))
        img.load() # Force the image data to load into memory
    except Exception as e:
        logger.error(f"Invalid image format: {str(e)}")
        raise HTTPException(status_code=422, detail="Invalid image format or corrupt file.")

    try:
        result = process_image(img, document_type or None)
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

# 8. WSGI Wrapper for cPanel (Passenger)
# --------------------------------------------------------------------------
from a2wsgi import ASGIMiddleware
application = ASGIMiddleware(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)