# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

# The embedding model is part of the image, downloaded here once: a pod never downloads anything when it starts (no
# 350 MB on every restart, nothing to reach out to from a restricted network, and the weights are the ones that were
# built and scanned). Another model is another build: `--build-arg EMBEDDING_MODEL=...`, and its vectors another
# collection (see app/config.py).
FROM builder AS model
ARG EMBEDDING_MODEL=google/siglip2-base-patch16-224
RUN /app/.venv/bin/python -c "\
import os; from fastembed import ImageEmbedding; \
ImageEmbedding(os.environ['EMBEDDING_MODEL'], cache_dir='/models')" \
    && find /models -name '.locks' -prune -exec rm -rf {} +

FROM python:3.13-slim AS runtime
# pip is a build tool: the runtime image never installs anything, and the pip bundled with the base
# image carries known CVEs. Removed rather than upgraded, so there is nothing left to keep patched.
RUN python -m pip uninstall -y pip
RUN useradd --create-home --uid 1000 worker
WORKDIR /app
COPY --from=builder --chown=worker:worker /app/.venv /app/.venv
COPY --from=builder --chown=worker:worker /app/app /app/app
COPY --from=model --chown=worker:worker /models /models
ARG EMBEDDING_MODEL=google/siglip2-base-patch16-224
USER worker
ENV PATH="/app/.venv/bin:$PATH" \
    EMBEDDING_MODEL=$EMBEDDING_MODEL \
    EMBEDDING_CACHE_DIR=/models \
    HF_HUB_OFFLINE=1
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD celery -A app.celery_app inspect ping -d celery@$HOSTNAME || exit 1
CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "-Q", "template_matching"]
