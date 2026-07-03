# Deployment

Docker-based deployment for Wakeel: a development stack at the repo root and a
production stack (nginx in front) in this folder.

> Requires Docker Engine with Compose **v2.24+** (the compose files use the
> `env_file: path/required` long syntax).

## Images

| Image | Dockerfile | Context | Notes |
|---|---|---|---|
| backend | `backend/Dockerfile` | **repo root** | Copies `backend/`, `agents/`, `shared/`, `database/`, `scripts/`, `data/` — backend imports the top-level packages, so never build it with `backend/` as context |
| frontend | `frontend/Dockerfile` | `frontend/` | Multi-stage: `dev` (hot reload) and `runner` (standalone production build) |
| mini-rag | `MIni-RAG-APP-V1/Dockerfile` | `MIni-RAG-APP-V1/` | Serves plain HTTP on 8001 inside the compose network |

## Local development

```bash
cp .env.example .env        # fill in Supabase, OpenAI, JWT values
docker compose up -d --build
```

- Frontend: http://localhost:3000 (hot reload — `frontend/` is bind-mounted)
- Backend: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Mini-RAG: http://localhost:8001
- Postgres (pgvector) on 5432, Redis on 6379

The Odoo sandbox is optional:

```bash
docker compose --profile erp up -d     # adds odoo (8069) + odoo-db
```

## Production (single host)

1. Put a filled-in `.env` at the repo root (set `APP_ENV=production`,
   strong `JWT_SECRET_KEY`, real Supabase/OpenAI keys).
2. Set the public origin used by the browser bundle, e.g. in `.env`:

   ```
   PUBLIC_BASE_URL=https://wakeel.example.com
   PUBLIC_WS_BASE_URL=wss://wakeel.example.com
   ```

3. Deploy:

   ```bash
   ./deployment/deploy.sh          # build + start + health check
   ./deployment/deploy.sh --pull   # git pull first
   ```

Only nginx publishes ports (80/443). It routes `/api/` and `/health` to the
backend and everything else to the Next.js frontend
(see [nginx/nginx.conf](nginx/nginx.conf)).

### HTTPS

Place `fullchain.pem` / `privkey.pem` in `deployment/nginx/certs/` (e.g. via
certbot on the host), then uncomment the 443 server block and the HTTP→HTTPS
redirect in [nginx/nginx.conf](nginx/nginx.conf) and reload:

```bash
docker compose -f deployment/docker-compose.prod.yml exec nginx nginx -s reload
```

## Notes

- **NEXT_PUBLIC_\* are build-time values.** Changing `PUBLIC_BASE_URL` requires
  rebuilding the frontend image (`deploy.sh` always rebuilds).
- The app database is **Supabase** (from `DATABASE_URL` in `.env`); the local
  `postgres` service in the dev compose is a pgvector-enabled sandbox for
  development, and is not part of the production stack.
- Backend containers read secrets from `.env` at runtime via `env_file` —
  secrets are never baked into images (`.dockerignore` excludes `.env`).
