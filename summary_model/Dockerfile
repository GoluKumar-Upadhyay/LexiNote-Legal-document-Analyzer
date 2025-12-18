FROM python:3.11-slim

# Install system packages required for Python wheels and performance
RUN apt-get update && apt-get install -y --no-install-recommends \

    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first so Docker can cache this layer if requirements don't change
COPY requirements.txt /app/

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip==23.3.1
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Copy and install the entrypoint that will materialize secrets into files
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create a non-root user for security and ensure /secrets is writable by that user
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /secrets \
    && chown -R appuser:appuser /app /secrets

USER appuser

# Cloud Run sets $PORT automatically; do not hardcode ENV PORT or EXPOSE

ENTRYPOINT ["/app/entrypoint.sh"]
CMD sh -c "gunicorn app:app --bind 0.0.0.0:$PORT --timeout 1200 --workers 1"