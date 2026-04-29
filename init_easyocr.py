import easyocr
try:
    reader = easyocr.Reader(['en', 'hi'], gpu=False)
    print("EasyOCR models initialized.")
except Exception as e:
    print(f"Error: {e}")
