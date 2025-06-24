# Multi-stage Dockerfile for Discord Pinball Map Bot

# Stage 1: Builder - Install dependencies
FROM python:3.13-slim-bullseye AS builder

# Install build dependencies including tools for Litestream
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install Litestream
RUN curl -L -o litestream-linux-amd64.tar.gz https://github.com/benbjohnson/litestream/releases/latest/download/litestream-linux-amd64.tar.gz && \
    curl -L -o litestream-linux-amd64.tar.gz.sha256 https://github.com/benbjohnson/litestream/releases/latest/download/litestream-linux-amd64.tar.gz.sha256 && \
    sha256sum -c litestream-linux-amd64.tar.gz.sha256 && \
    tar -C /usr/local/bin -xzf litestream-linux-amd64.tar.gz litestream && \
    rm litestream-linux-amd64.tar.gz litestream-linux-amd64.tar.gz.sha256

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

# Copy Litestream binary from builder stage
COPY --from=builder /usr/local/bin/litestream /usr/local/bin/litestream

# Copy application source code
COPY src/ /app/src/
COPY bot.py /app/

# Copy Litestream configuration and startup script
COPY litestream.yml /app/litestream.yml
COPY startup.sh /app/startup.sh

# Make startup script executable
RUN chmod +x /app/startup.sh

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

# Set the entrypoint to use startup script for Litestream + bot coordination
ENTRYPOINT ["/app/startup.sh"]
