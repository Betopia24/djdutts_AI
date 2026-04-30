FROM python:3.12-slim

# Set working directory
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create data directory for FAISS index persistence
RUN mkdir -p /app/data

# Run as a non-root user
RUN useradd --create-home --shell /bin/bash appuser \
	&& chown -R appuser:appuser /app

USER appuser

# Expose port 8011
EXPOSE 8011

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8011/docs')"
