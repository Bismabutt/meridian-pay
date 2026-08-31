# ---- Base image ----
FROM python:3.12-slim AS base

# ---- Environment ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ---- Working directory ----
WORKDIR /app

# ---- OS dependencies ----
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies (cached separately from code) ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Non-root user ----
RUN useradd --create-home --shell /bin/bash --uid 1001 appuser

# ---- Application code ----
COPY --chown=appuser:appuser app/ ./app/
USER appuser

# ---- Runtime ----
EXPOSE 8007
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]