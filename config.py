import os
from dotenv import load_dotenv

load_dotenv()

# Tesseract binary path — Linux default; update via .env for Windows
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    "/usr/bin/tesseract"
)

# Upload settings
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 10))
ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}

# OCR settings
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "eng")
TESSERACT_CONFIG = os.getenv("TESSERACT_CONFIG", "--oem 3 --psm 6")

# Service settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8001))
API_KEY = os.getenv("API_KEY", "your-secret-api-key-change-this")
