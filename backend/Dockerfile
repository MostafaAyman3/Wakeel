# syntax=docker/dockerfile:1
# Backend image — MUST be built from the repository root:
#   docker build -f backend/Dockerfile .
# because backend code imports the top-level `agents` and `shared` packages.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so code changes don't bust the pip cache layer.
COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY agents/requirements.txt /tmp/agents-requirements.txt
RUN pip install -r /tmp/backend-requirements.txt -r /tmp/agents-requirements.txt

# Only what the API needs at runtime — no frontend, docs, or Mini-RAG.
COPY backend/ backend/
COPY agents/ agents/
COPY shared/ shared/
COPY database/ database/
COPY scripts/ scripts/
COPY data/ data/

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
