#!/usr/bin/env bash
# Wakeel — single-host production deploy.
#
# Usage (from anywhere on the server):
#   ./deployment/deploy.sh            # build + (re)start the prod stack
#   ./deployment/deploy.sh --pull     # git pull first, then deploy
#
# Prerequisites: docker + docker compose v2, and a filled-in .env at repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.prod.yml"

cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found at $REPO_ROOT/.env — copy .env.example and fill it in." >&2
    exit 1
fi

if [[ "${1:-}" == "--pull" ]]; then
    echo "==> Pulling latest code"
    git pull --ff-only
fi

echo "==> Building images"
docker compose -f "$COMPOSE_FILE" build --pull

echo "==> Starting stack"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "==> Waiting for health endpoint"
for i in $(seq 1 30); do
    if curl -fsS http://localhost/health >/dev/null 2>&1; then
        echo "==> Deploy OK — http://localhost/health is answering"
        docker compose -f "$COMPOSE_FILE" ps
        exit 0
    fi
    sleep 5
done

echo "ERROR: stack did not become healthy within 150s" >&2
docker compose -f "$COMPOSE_FILE" ps
docker compose -f "$COMPOSE_FILE" logs --tail=50 backend nginx
exit 1
