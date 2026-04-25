import os
from dotenv import load_dotenv

load_dotenv()

# Tesseract binary path — Linux default; update via .env for Windows
# Tesseract binary path
# We try to detect the environment and fallback if the path in .env is invalid for the OS
_TESS_ENV = os.getenv("TESSERACT_CMD", "")
if os.name == 'posix':  # Linux/Mac
    # If .env has a Windows path or is empty, use Linux default
    if not _TESS_ENV or ":" in _TESS_ENV or not os.path.exists(_TESS_ENV):
        TESSERACT_CMD = "/usr/bin/tesseract"
    else:
        TESSERACT_CMD = _TESS_ENV
else:  # Windows
    TESSERACT_CMD = _TESS_ENV or r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Upload settings
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 10))
ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}

# OCR settings
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "eng")
TESSERACT_CONFIG = os.getenv("TESSERACT_CONFIG", "--oem 3 --psm 6")

# Service settings
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8001))
API_KEY = os.getenv("API_KEY", "your-secret-api-key-change-this")
