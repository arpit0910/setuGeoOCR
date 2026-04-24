import requests

url = "http://localhost:8001/ocr/extract"
headers = {"X-API-KEY": "your-secret-api-key-change-this"}
files = {"image": ("test_img.png", open("test_img.png", "rb"), "image/png")}

try:
    response = requests.post(url, headers=headers, files=files)
    print("Status Code:", response.status_code)
    print("Response Body:", response.json())
except Exception as e:
    print("Error:", e)
