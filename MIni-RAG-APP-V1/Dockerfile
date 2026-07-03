# syntax=docker/dockerfile:1
# Mini-RAG microservice (PDF chunking / embedding / retrieval).
# Runs plain HTTP inside the compose network — the root main.py's
# self-signed-HTTPS launcher is for standalone dev only.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NLTK_DATA=/usr/local/share/nltk_data

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && python -m nltk.downloader -d "$NLTK_DATA" punkt punkt_tab

COPY src/ ./src/

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# src/main.py imports its siblings as top-level modules (from routes import …),
# so uvicorn must run with src as the working directory.
WORKDIR /app/src

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
