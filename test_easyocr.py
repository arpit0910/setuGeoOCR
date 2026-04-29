import easyocr
import numpy as np
from PIL import Image
import os
import json

# verbose=False might help
reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)

files = ["pancard.png", "aadhaar_front.png", "aadhaar_back.png"]

for filename in files:
    print(f"\n--- Testing {filename} with EasyOCR ---")
    if not os.path.exists(filename):
        print("File not found")
        continue
        
    img = Image.open(filename)
    img_np = np.array(img.convert('RGB'))
    results = reader.readtext(img_np)
    
    text = " ".join([res[1] for res in results])
    print(f"Full Text: {text[:200]}...")
    
    print("Detected Text Blocks:")
    for res in results:
        print(f" - {res[1]}")
