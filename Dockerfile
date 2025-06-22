# Multi-stage Dockerfile for Discord Pinball Map Bot

# Stage 1: Builder - Install dependencies
FROM python:3.13-slim-bullseye AS builder

# Install PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM python:3.13-slim-bullseye

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY src/ /app/src/
COPY bot.py /app/

# Set working directory
WORKDIR /app

# Set PATH to include virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables for optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONOPTIMIZE=2

# Set memory limits for Python
ENV PYTHONMALLOC=malloc
ENV PYTHONMALLOCSTATS=1

# Switch to non-root user
USER appuser

# Expose port for health checks (Cloud Run will set PORT env var)
EXPOSE 8080

# Set the entrypoint with proper signal handling
ENTRYPOINT ["python", "-u", "bot.py"]
