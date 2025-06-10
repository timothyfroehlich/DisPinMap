# Multi-stage Dockerfile for Discord Pinball Map Bot

# Stage 1: Builder - Install dependencies
FROM python:3.11-slim-bullseye AS builder

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM python:3.11-slim-bullseye

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY src/ /app/src/
COPY bot.py /app/
COPY *.md /app/

# Set working directory
WORKDIR /app

# Set PATH to include virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Expose port for health checks (Cloud Run will set PORT env var)
EXPOSE 8080

# Set the entrypoint
CMD ["python", "bot.py"]