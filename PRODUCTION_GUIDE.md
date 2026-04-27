# SetuGeo OCR Service - Production Deployment Guide

This microservice is designed to be production-ready and easily integrated with a Laravel application.

## 🚀 Deployment (Standard Python Hosting / VPS)

If you are using a hosting panel (like cPanel, A2Hosting, etc.) to host a "Python App":

1.  **Application Root**: `setuGeoOCR`
2.  **Application Startup File**: `main.py`
3.  **Application Entry Point**: `app` (if they support ASGI) or `wsgi_app` (if they only support WSGI)
4.  **Passenger / Configuration**: Point to `main.py`.

### 🐳 Deployment (Docker)
...

1.  **Configure Environment**:
    Create a `.env` file from `.env.example`:
    ```bash
    cp .env.example .env
    ```
    Set a strong `API_KEY` in the `.env` file.

2.  **Run with Docker Compose**:
    ```bash
    docker-compose up -d --build
    ```
    The service will be available at `http://localhost:8001`.

## 🛠 Laravel Integration

In your Laravel project, you can use the `Illuminate\Support\Facades\Http` client.

### Example: Calling the OCR Service

```php
use Illuminate\Support\Facades\Http;
use Illuminate\Http\UploadedFile;

public function processDocument(UploadedFile $file)
{
    $apiUrl = config('services.ocr.url', 'https://api.setugeo.com');
    $apiKey = config('services.ocr.key');

    $response = Http::withHeaders([
        'X-API-KEY' => $apiKey
    ])
    ->attach('image', file_get_contents($file->path()), $file->getClientOriginalName())
    ->post($apiUrl . '/ocr/extract', [
        'document_type' => 'pan' // optional: pan, aadhaar_front, aadhaar_back
    ]);

    if ($response->successful()) {
        return $response->json();
    }

    return response()->json(['error' => 'OCR failed'], 500);
}
```

### Response Format

```json
{
  "document_type": "pan",
  "raw_text": "...",
  "extracted_fields": {
    "pan_number": "ABCDE1234F",
    "name": "John Doe",
    "father_name": "Richard Doe",
    "dob": "01/01/1990",
    "card_type": "Individual"
  },
  "confidence": "high"
}
```

## 📈 Monitoring

- **Health Check**: `GET /health` returns status and tesseract engine version.
- **API Docs**: `GET /docs` (Swagger UI).
- **Logs**: Standard out (seen via `docker logs`) and `ocr_service.log` file.

## 🔒 Security

- The service is protected by `X-API-KEY` header.
- CORS is enabled for all origins by default; modify `main.py` if you need to restrict it to your Laravel frontend domain.

## 🛠 CPanel Troubleshooting

If you encounter issues when deploying to cPanel:

### 1. 404 Not Found (Subdomain issue)
- Ensure your subdomain (`api.setugeo.com`) is pointing to the folder containing the project.
- Check `.htaccess`. The `PassengerAppRoot` must be the **absolute path** to your project folder (e.g., `/home/username/setuGeoOCR`).

### 2. 500 Internal Server Error / FastAPI Boot Error
- This usually means a dependency is missing or the WSGI bridge failed.
- **Check `.env`**: Ensure `TESSERACT_CMD` is NOT a Windows path (like `C:\...`). The app will try to auto-detect `/usr/bin/tesseract` on Linux, but a Windows path in `.env` will override it and fail.
- **Install dependencies**: Use the cPanel "Setup Python App" interface to run `pip install -r requirements.txt`.
- **Passenger WSGI**: Ensure the "Application Startup File" is set to `passenger_wsgi.py` in the cPanel interface.

### 3. Tesseract Not Found
- cPanel servers often do not have Tesseract installed by default.
- You may need to ask your hosting provider to install it, or use a VPS where you can run `sudo apt install tesseract-ocr`.
- Check the `/health` endpoint to see if Tesseract is detected.

### 4. Permissions
- Ensure the `ocr_service.log` and `uploads/` directory are writable by the account user.
- If the app won't start, check the `stderr.log` (if configured in cPanel) or look for a file named `error_log` in the project root.

### 5. Request Timeout / Infinite Loader
- **Symptoms**: The page shows a loading indicator forever or returns a 'Request Timeout' error (504).
- **Cause**: The Python process is taking too long to respond to the initial request, often due to resource limits (threads) or blocking initialization.
- **Fixes Applied**:
    - We have moved all routes to 'async def' and use 'run_in_threadpool' for OCR tasks to prevent blocking the event loop.
    - We have added strict environment variable thread limiting at the absolute top of 'main.py' and 'passenger_wsgi.py' (e.g., 'OPENBLAS_NUM_THREADS=1').
- **Required Action**: If the live site ('https://api.setugeo.com') still times out, ensure the **Absolute Paths** in '.htaccess' are correct for your current server (check if '/home/outgglmv/' is still your username).
- **Frontend Timeout**: The 'index.html' now has a 60-second timeout built-in to prevent the UI from hanging if the server is slow.
