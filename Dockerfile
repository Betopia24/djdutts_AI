FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create data directory for FAISS index persistence
RUN mkdir -p /app/data

# Expose port 8011
EXPOSE 8011

# Run the application
CMD ["python", "main.py"]
