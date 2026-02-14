FROM python:3.11.14-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask==3.1.2 requests==2.32.5

# Copy application
COPY app.py .

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["python", "app.py"]
