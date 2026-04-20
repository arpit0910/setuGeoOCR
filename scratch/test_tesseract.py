import pytesseract
import config
import os

pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

try:
    version = pytesseract.get_tesseract_version()
    print(f"Tesseract Version: {version}")
    langs = pytesseract.get_languages()
    print(f"Supported Languages: {langs}")
    print("SUCCESS: Pytesseract is correctly linked to the Tesseract binary.")
except Exception as e:
    print(f"ERROR: Could not connect to Tesseract. {e}")
