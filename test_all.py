import os
from PIL import Image
from ocr_processor import process_image
import json

files = [
    ("pancard.png", "pan"),
    ("aadhaar_front.png", "aadhaar_front"),
    ("aadhaar_back.png", "aadhaar_back"),
]

for filename, doc_type in files:
    print(f"\n========== Testing {filename} ==========")
    if os.path.exists(filename):
        img = Image.open(filename)
        result = process_image(img, doc_type)
        print(f"Status: {'SUCCESS' if result['success'] else 'FAILED'}")
        print("Extracted Fields:")
        print(json.dumps(result["extracted_fields"], indent=2))
        if not result["success"]:
            print(f"Message: {result['message']}")
    else:
        print("File not found")
