import requests

url = "http://127.0.0.1:8001/ocr/extract"
headers = {"X-API-KEY": "your-secret-api-key-change-this"}
files = {"image": ("pancard.png", open("pancard.png", "rb"), "image/png")}
data = {"document_type": "pan"}

response = requests.post(url, headers=headers, files=files, data=data)
print("Status:", response.status_code)
print("Response:", response.text)
