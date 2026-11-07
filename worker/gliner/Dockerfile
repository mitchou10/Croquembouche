# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

# The GLiNER model (and the tokenizer it is built on) is part of the image, downloaded here once: a pod never downloads
# anything when it starts. Another model is another build: `--build-arg GLINER_MODEL=...`.
FROM builder AS model
ARG GLINER_MODEL=urchade/gliner_multi-v2.1
ENV HF_HOME=/models/hf GLINER_MODEL=$GLINER_MODEL
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN /app/.venv/bin/python -c "\
import os; from gliner import GLiNER; GLiNER.from_pretrained(os.environ['GLINER_MODEL'])" \
    && find /models -name '.locks' -prune -exec rm -rf {} +

FROM python:3.13-slim AS runtime
# pip is a build tool: the runtime image never installs anything, and the pip bundled with the base
# image carries known CVEs. Removed rather than upgraded, so there is nothing left to keep patched.
RUN python -m pip uninstall -y pip
# What torch loads at import.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 worker
WORKDIR /app
COPY --from=builder --chown=worker:worker /app/.venv /app/.venv
COPY --from=builder --chown=worker:worker /app/app /app/app
COPY --from=model --chown=worker:worker /models /models
ARG GLINER_MODEL=urchade/gliner_multi-v2.1
USER worker
ENV PATH="/app/.venv/bin:$PATH" \
    GLINER_MODEL=$GLINER_MODEL \
    HF_HOME=/models/hf \
    HF_HUB_OFFLINE=1
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD celery -A app.celery_app inspect ping -d celery@$HOSTNAME || exit 1
CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "-Q", "gliner"]
