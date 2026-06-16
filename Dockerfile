# Use the official Python 3.10 slim image as the base to minimize image size
FROM python:3.10-slim

# Create a non-root group and user (uid/gid 1000) to reduce the container attack surface
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements.txt first so that the dependency installation layer is
# cached independently of application source changes — rebuilds only when
# requirements change
COPY requirements.txt .

# Install Python dependencies without caching to keep the layer size minimal
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application source code
COPY app.py .

# Inform Docker (and tooling) that the container listens on port 5000
EXPOSE 5000

# Switch to the non-root user before running the application
USER appuser

# Default command: start the Flask application
CMD ["python", "app.py"]
