# Use lightweight Python base
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install dependencies inside virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the .env file (if exists) and ensure it is used
COPY .env /app/.env
ENV $(cat /app/.env | xargs)

# Use environment variables
ENV PYTHONUNBUFFERED=1

# Copy app code
COPY . .

# Start command (now uses the virtual environment)
CMD ["uvicorn", "mistral:app", "--host", "0.0.0.0", "--port", "8000"]