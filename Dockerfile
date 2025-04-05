FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/bakta_data /app/results

# Set environment variables
ENV PYTHONPATH=/app
ENV BAKTA_DATA_DIR=/app/bakta_data
ENV RESULTS_DIR=/app/results

# Expose the API port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "amr_predictor.web.api:app", "--host", "0.0.0.0", "--port", "8000"]
