import io
from PIL import Image
from ocr_processor import process_image
import os
import json

files = ["pancard.png", "aadhaar_front.png", "aadhaar_back.png"]

for filename in files:
    print(f"\n--- Testing {filename} ---")
    if not os.path.exists(filename):
        print("File not found")
        continue
        
    img = Image.open(filename)
    result = process_image(img)
    
    print(f"Document Type: {result['document_type']}")
    print(f"Confidence: {result['confidence']}")
    # Use ensure_ascii=True for terminal output safety, or just print keys
    print("Extracted Fields Keys:", list(result['extracted_fields'].keys()))
    try:
        # Try to print safely
        fields_str = json.dumps(result['extracted_fields'], indent=2, ensure_ascii=False)
        print("Extracted Fields (Raw):", fields_str.encode('utf-8', errors='replace').decode('ascii', errors='replace'))
    except:
        print("Extracted Fields (ASCII):", json.dumps(result['extracted_fields'], indent=2, ensure_ascii=True))
        
    print(f"Validation: {result['validation']['message']}")
