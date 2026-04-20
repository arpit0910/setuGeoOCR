import os
from dotenv import load_dotenv

load_dotenv()

# Tesseract binary path — update this if Tesseract is installed elsewhere
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
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
