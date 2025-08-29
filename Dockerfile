FROM python:3.9-slim

LABEL maintainer="TechBot Team"
LABEL description="TechBot Marketplace - Clean Architecture"
LABEL version="3.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r techbot && useradd -r -g techbot techbot

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY marketplace_bot_refactored.py .
COPY pyproject.toml .

# Create necessary directories
RUN mkdir -p logs uploads wallets && \
    chown -R techbot:techbot /app

# Switch to non-root user
USER techbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app; print('OK')" || exit 1

# Default command
CMD ["python", "marketplace_bot_refactored.py"]