# Use an official Python runtime as a parent image
FROM python:3.10.19-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Pre-download EasyOCR models (English and Hindi)
RUN python -c "import easyocr; reader = easyocr.Reader(['en', 'hi'], gpu=False)"

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application using uvicorn
# We use multiple workers for production
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
