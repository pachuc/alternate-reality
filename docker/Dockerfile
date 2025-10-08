FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements/base.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "src.proxy"]