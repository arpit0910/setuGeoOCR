from doctr.models import ocr_db_resnet50, ocr_predictor
import os
import time
from PIL import Image
import numpy as np

# Load the model once
predictor = ocr_predictor(pretrained=True)

filename = "pancard.png"
if os.path.exists(filename):
    start = time.time()
    # doctr works best with lists
    result = predictor([filename])
    print(f"DocTR Time: {time.time() - start:.2f}s")
    
    # Export results
    json_export = result.export()
    print("Detected some text blocks:", len(json_export['pages'][0]['blocks']))
