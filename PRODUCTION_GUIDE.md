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
    $apiUrl = config('services.ocr.url', 'https://ocr.setugeo.com');
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
