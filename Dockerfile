FROM python:3.11-slim

# Install system dependencies for HEIC
RUN apt-get update && apt-get install -y \
    libheif-dev \
    libheif1 \
    libde265-dev \
    libx265-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE $PORT

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
