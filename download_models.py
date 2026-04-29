import urllib.request
import zipfile
import os

model_dir = os.path.join(os.getcwd(), "models", "easyocr")
os.makedirs(model_dir, exist_ok=True)

models = {
    "craft_mlt_25k.zip": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/craft_mlt_25k.zip",
    "english_g2.zip": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
}

headers = {'User-Agent': 'Mozilla/5.0'}

for name, url in models.items():
    path = os.path.join(model_dir, name)
    if not os.path.exists(path.replace(".zip", ".pth")):
        print(f"Downloading {name}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
            out_file.write(response.read())
            
        print(f"Unzipping {name}...")
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(model_dir)
        os.remove(path)
    else:
        print(f"{name} already exists.")

print("Done.")
