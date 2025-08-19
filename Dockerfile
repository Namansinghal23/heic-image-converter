FROM python:3.11-slim

# Install system dependencies for HEIC
RUN apt-get update && apt-get install -y \
    libheif-dev \
    libheif1 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Use Railway's PORT or default to 8080
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8080}
