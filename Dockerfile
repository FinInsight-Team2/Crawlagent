# ========================================
# CrawlAgent Dockerfile
# Multi-stage build for production deployment
# ========================================
# Build: docker build -t crawlagent:latest .
# Run: docker-compose up -d

# ========================================
# Stage 1: Builder (Dependencies)
# ========================================
FROM python:3.11-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Export dependencies to requirements.txt
# This allows us to use pip in the runtime stage (faster, smaller image)
RUN poetry export -f requirements.txt -o requirements.txt --without-hashes

# ========================================
# Stage 2: Runtime (Application)
# ========================================
FROM python:3.11-slim

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 crawlagent && \
    mkdir -p /app /app/logs /app/htmlcov && \
    chown -R crawlagent:crawlagent /app

# Set working directory
WORKDIR /app

# Copy requirements from builder
COPY --from=builder /app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=crawlagent:crawlagent . .

# Switch to non-root user
USER crawlagent

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

# Expose Gradio port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7860 || exit 1

# Default command: Run Gradio UI
CMD ["python", "-m", "src.ui.app"]
