# Use lightweight Python base
FROM python:3.11-slim

# Set environment variable for Mistral API Key
ENV MISTRAL_API_KEY="fVLsPcXstWczO0MOriDzGPzpScdzCGvN"

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

# Use environment variables
ENV PYTHONUNBUFFERED=1

# Copy app code
COPY . .

# Start command (uses virtual environment)
CMD ["uvicorn", "blackbox:app", "--host", "0.0.0.0", "--port", "8000"]