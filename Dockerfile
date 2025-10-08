FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY wikipedia_proxy.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "wikipedia_proxy.py"]