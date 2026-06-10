# syntax=docker/dockerfile:1.6
# Build multi-fase para que la imagen final sea más ligera

# --- Tailwind (binario standalone, sin Node) ---
FROM debian:bookworm-slim AS tailwind
ARG TAILWIND_VERSION=v3.4.17
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Descarga el binario pinneado de Tailwind v3 para linux-x64.
# (Reproducible por versión; idealmente verificar checksum del release.)
RUN curl -fsSL -o /usr/local/bin/tailwindcss \
        "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64" \
    && chmod +x /usr/local/bin/tailwindcss
# Solo lo que el escáner de contenido necesita para purgar utilidades.
COPY tailwind.config.js ./
COPY static ./static
COPY templates ./templates
RUN tailwindcss \
        -c tailwind.config.js \
        -i static/css/tailwind.input.css \
        -o static/css/tailwind.build.css \
        --minify

# --- Builder ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# --- Runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=flowly.settings.production

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=app:app . /app
# CSS de Tailwind compilado, colocado ANTES de collectstatic para que
# WhiteNoise (CompressedManifestStaticFilesStorage) lo hashee/comprima.
COPY --from=tailwind --chown=app:app /app/static/css/tailwind.build.css /app/static/css/tailwind.build.css

RUN DJANGO_SECRET_KEY=build-time DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

RUN chmod +x /app/docker-entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn flowly.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-1} --access-logfile -"]
