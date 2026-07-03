# syntax=docker/dockerfile:1
# Multi-stage frontend image.
#   dev    → hot-reload server for docker-compose local development
#   runner → minimal production image using Next.js standalone output

# ── Dependencies ─────────────────────────────────────────────────
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ── Development (hot reload) ─────────────────────────────────────
FROM node:20-alpine AS dev
WORKDIR /app
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

# ── Production build ─────────────────────────────────────────────
FROM node:20-alpine AS builder
RUN apk add --no-cache libc6-compat
WORKDIR /app
# NEXT_PUBLIC_* vars are inlined into the client bundle at build time,
# so they must be provided as build args, not runtime env.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_WS_BASE_URL=$NEXT_PUBLIC_WS_BASE_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── Production runtime ───────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system nodejs && adduser --system nextjs --ingroup nodejs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
