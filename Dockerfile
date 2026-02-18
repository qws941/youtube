# ============================================
# YouTube Automation System - Docker Image
# ============================================
FROM python:3.14-slim AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto-cjk \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 ytauto \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home ytauto

WORKDIR /app

# ============================================
# Builder stage - install dependencies
# ============================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (cache optimization)
COPY pyproject.toml .
COPY src/__init__.py src/

# Install Python dependencies
RUN pip install --user -e .

# ============================================
# Production stage
# ============================================
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /root/.local /home/ytauto/.local

# Copy application code
COPY --chown=ytauto:ytauto . .

# Create data directories
RUN mkdir -p data/output data/assets data/templates config \
    && chown -R ytauto:ytauto data config

# Switch to non-root user
USER ytauto

# Add local bin to PATH
ENV PATH="/home/ytauto/.local/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.cli import app; print('healthy')" || exit 1

# Default command
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]
