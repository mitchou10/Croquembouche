# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

# The OCR models are part of the image, downloaded here once: a pod never downloads anything when it starts.
# Other models are another build: `--build-arg OCR_DET_MODEL=... --build-arg OCR_REC_MODEL=...`.
FROM builder AS model
ARG OCR_DET_MODEL=PP-OCRv6_tiny_det
ARG OCR_REC_MODEL=PP-OCRv6_tiny_rec
ENV PADDLE_PDX_CACHE_HOME=/models PADDLE_PDX_MODEL_SOURCE=huggingface OCR_DET_MODEL=$OCR_DET_MODEL OCR_REC_MODEL=$OCR_REC_MODEL
# What Paddle and OpenCV load at import: the build fails without them (libgomp.so.1 for Paddle).
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN /app/.venv/bin/python -c "\
from app import ocr; ocr.get_engine()"

FROM python:3.13-slim AS runtime
RUN python -m pip uninstall -y pip
# Paddle and OpenCV load these at import.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 worker
WORKDIR /app
COPY --from=builder --chown=worker:worker /app/.venv /app/.venv
COPY --from=builder --chown=worker:worker /app/app /app/app
COPY --from=model --chown=worker:worker /models /models
ARG OCR_DET_MODEL=PP-OCRv6_tiny_det
ARG OCR_REC_MODEL=PP-OCRv6_tiny_rec
USER worker
ENV PATH="/app/.venv/bin:$PATH" \
    OCR_DET_MODEL=$OCR_DET_MODEL \
    OCR_REC_MODEL=$OCR_REC_MODEL \
    PADDLE_PDX_CACHE_HOME=/models \
    PADDLE_PDX_MODEL_SOURCE=huggingface \
    DISABLE_MODEL_SOURCE_CHECK=True
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD celery -A app.celery_app inspect ping -d celery@$HOSTNAME || exit 1
CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "-Q", "ocr"]
