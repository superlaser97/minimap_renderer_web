FROM python:3.11-slim

# Install system dependencies required for Pillow and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
# Copy the minimap_renderer directory
COPY minimap_renderer /app/minimap_renderer

# Copy the backend code to /app/web_wrapper/backend
COPY web_wrapper/backend /app/web_wrapper/backend

# Set working directory to where main.py is
WORKDIR /app/web_wrapper/backend

# Create necessary directories
RUN mkdir -p uploads outputs

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
