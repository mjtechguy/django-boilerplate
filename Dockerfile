# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt pyproject.toml ./
RUN pip install --upgrade pip uv && \
    uv pip install --system -r requirements.txt -r requirements-dev.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.local

CMD ["bash", "-c", "python backend/manage.py migrate && python backend/manage.py runserver 0.0.0.0:8000"]
