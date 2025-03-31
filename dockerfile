# Use lightweight Python base
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the .env file (if exists) and ensure it is used
COPY .env /app/.env

# Use environment variables
ENV PYTHONUNBUFFERED=1

# Copy app code
COPY . .

# Start command
CMD ["uvicorn", "mistral:app", "--host", "0.0.0.0", "--port", "8000"]