import os
from PIL import Image
from ocr_processor import process_image

files = [
    ("aadhaar_front.png", "aadhaar_front"),
    ("aadhaar_back.png", "aadhaar_back"),
]

for filename, doc_type in files:
    print(f"--- Processing {filename} ---")
    if os.path.exists(filename):
        img = Image.open(filename)
        result = process_image(img, doc_type)
        print("Raw text snippet:", repr(result["raw_text"][:200]))
        print("Extracted fields:", result["extracted_fields"])
        print("Success:", result["success"])
        print("Message:", result["message"])
    else:
        print("File not found")
