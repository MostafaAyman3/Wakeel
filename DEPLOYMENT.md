# Wakeel — Deployment Guide

Deploy Wakeel as a **polished public demo** with two services:

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend (Next.js) | **Vercel** | `https://wakeel.vercel.app` |
| Backend (FastAPI + LangGraph) | **Render** | `https://wakeel-api.onrender.com` |
| Database | **Supabase** | Already configured |

---

## Prerequisites

- [x] GitHub account with this repo pushed
- [x] Supabase project with PostgreSQL configured
- [x] OpenAI API key
- [ ] Vercel account → [vercel.com](https://vercel.com)
- [ ] Render account → [render.com](https://render.com)

---

## Step 1: Deploy Backend on Render

### 1.1 Create Render Account

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Sign up with GitHub (recommended)

### 1.2 Deploy via Blueprint (Recommended)

1. Push this repo to GitHub
2. Go to [dashboard.render.com/blueprints](https://dashboard.render.com/blueprints)
3. Click **"New Blueprint Instance"**
4. Select your `Wakeel` repository
5. Render reads `render.yaml` and creates the service automatically
6. Fill in the environment variables:

| Variable | Value | Required |
|----------|-------|----------|
| `DATABASE_URL` | Your Supabase pooler URL (asyncpg format) | ✅ |
| `READONLY_DB_URL` | Your Supabase readonly URL | ✅ |
| `OPENAI_API_KEY` | `sk-proj-...` | ✅ |
| `JWT_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | ✅ |
| `FRONTEND_BASE_URL` | Your Vercel URL (set after Step 2) | ✅ |
| `ELEVENLABS_API_KEY` | Optional — voice falls back to OpenAI TTS | ❌ |
| `LANGCHAIN_API_KEY` | Optional — for LangSmith tracing | ❌ |

7. Click **"Apply"** → Render starts building

### 1.3 Alternative: Manual Deploy

1. Click **"New Web Service"** in Render Dashboard
2. Connect your GitHub repo
3. Configure:
   - **Name**: `wakeel-api`
   - **Region**: `Frankfurt (EU Central)` or closest to your Supabase
   - **Branch**: `feature/vercel-deployment`
   - **Root Directory**: _(leave empty — project root)_
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables (same as table above)
5. Click **"Create Web Service"**

### 1.4 Verify Backend

Once deployed, visit:
```
https://your-render-url.onrender.com/health
```

Expected response:
```json
{"status": "ok", "app": "Wakeel", "version": "0.1.0", "env": "production"}
```

Also check the API docs:
```
https://your-render-url.onrender.com/docs
```

---

## Step 2: Deploy Frontend on Vercel

### 2.1 Import Project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: `Next.js` (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)

### 2.2 Set Environment Variables

In **Settings → Environment Variables**, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://wakeel-api.onrender.com` (your Render URL) |
| `NEXT_PUBLIC_APP_NAME` | `Wakeel` |
| `NEXT_PUBLIC_JWT_SECRET` | Same value as `JWT_SECRET_KEY` on Render |

### 2.3 Deploy

Click **"Deploy"** — Vercel builds and deploys automatically.

### 2.4 Update Render CORS

After you get your Vercel URL (e.g. `https://wakeel-xxx.vercel.app`):

1. Go to Render Dashboard → your service → Environment
2. Set `FRONTEND_BASE_URL` = your Vercel URL
3. Click **"Save Changes"** → Render auto-redeploys

---

## Step 3: Verify End-to-End

1. **Landing Page**: Open your Vercel URL → Module cards visible
2. **M1 Chat**: Click "Financial Analyst" → Send a query → Chart/table response
3. **M2 Dashboard**: Click "Procurement" → Inventory table → Click "Analyze"
4. **M3 Support**: Click "Customer Support" → Send message → AI response + Review panel
5. **Module Switcher**: Navigate between modules via header tabs
6. **Language Toggle**: Switch Arabic ↔ English

---

## Architecture

```
Browser → Vercel (Next.js) → [Vercel Rewrite Proxy] → Render (FastAPI)
                                                          ↓
                                                    Supabase (PostgreSQL)
                                                          ↓
                                                    OpenAI API
```

Vercel rewrites `/api/*` requests to the Render backend transparently.
The browser only sees the Vercel domain — no CORS issues.

---

## Troubleshooting

### "502 Bad Gateway" on API calls
- Render free tier sleeps after 15 minutes of inactivity
- First request after sleep takes ~30 seconds (cold start)
- This is normal for free tier

### CORS errors
- Ensure `FRONTEND_BASE_URL` on Render matches your Vercel URL exactly
- The backend also allows `*.vercel.app` regex for preview deployments

### "Connection error" in M1 Chat
- Verify the backend is running: check `https://your-render-url/health`
- Verify `NEXT_PUBLIC_API_BASE_URL` in Vercel matches your Render URL

### M2 Voice not working
- Voice requires OpenAI API key (for Whisper STT)
- ElevenLabs is optional — falls back to OpenAI TTS automatically
- Ensure microphone access is allowed in the browser

### M3 RAG not returning context
- This is expected if Mini-RAG microservice is not deployed
- M3 works fully without RAG — the graph continues with empty context
- To enable RAG, deploy the Mini-RAG service and set `MINI_RAG_BASE_URL`
