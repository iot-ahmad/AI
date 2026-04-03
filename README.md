# 🤖 AI Social Media Content System

Fully automated pipeline: **Trend Detection → AI Script → Video → Auto-Publish**

Runs on **free-tier** Render or Railway. Zero cost to get started.

---

## Architecture

```
Cron (every 6h)
    └── trend_service.py   ← Google Trends (pytrends) + seed fallback
    └── ai_service.py      ← OpenAI gpt-3.5-turbo (one call per trend)
    └── video_service.py   ← gTTS voiceover + Pillow image + FFmpeg encode
    └── publish_service.py ← Twitter API v2 + YouTube Data API v3
```

---

## Quick Start (local)

### 1. Clone & set up environment

```bash
git clone <your-repo>
cd app
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install dependencies

```bash
# System: FFmpeg required
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg fonts-dejavu-core

pip install -r requirements.txt
```

### 3. Run

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 — you should see `{"status": "running"}`.

### 4. Trigger pipeline manually

```bash
curl -X POST http://localhost:8000/run-pipeline
```

---

## Deploy to Render (FREE tier)

### Option A — One-click via render.yaml

1. Push this folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your repo — Render detects `render.yaml` automatically
4. Add your secret environment variables in the Render dashboard
5. Deploy — done ✅

### Option B — Manual

1. New Web Service → Docker runtime
2. Set **Build Command**: _(leave blank — Dockerfile handles it)_
3. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all env vars from `.env.example`
5. Free plan → Deploy

> ⚠️ Render free tier **spins down after 15 min of inactivity**.  
> The scheduler keeps the app alive as long as it runs at least once every 14 min.  
> Add a free uptime monitor (e.g. UptimeRobot → ping `/health` every 10 min).

---

## Deploy to Railway (FREE tier)

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Set environment variables:
```bash
railway variables set OPENAI_API_KEY=sk-...
railway variables set TWITTER_BEARER_TOKEN=...
# etc.
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Health check (for uptime monitors) |
| POST | `/run-pipeline` | Trigger full pipeline now |
| POST | `/run-trends` | Fetch & log trending topics |
| GET | `/scheduler/jobs` | View scheduled jobs + next run times |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for AI content |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Change to `gpt-4o-mini` for better quality |
| `NICHE_KEYWORDS` | `AI,motivation,...` | Comma-separated niches to filter |
| `PIPELINE_INTERVAL_HOURS` | `6` | How often to run the pipeline |
| `OUTPUT_DIR` | `/tmp/output` | Where videos are saved |
| `TWITTER_*` | — | Twitter OAuth 1.0a credentials |
| `YOUTUBE_CLIENT_SECRETS` | — | YouTube OAuth JSON (minified string) |

---

## Cost Estimate (monthly)

| Service | Free Tier | Paid if exceeded |
|---------|-----------|-----------------|
| Render/Railway | 750 hrs/mo | ~$7/mo |
| OpenAI gpt-3.5-turbo | — | ~$0.05/100 runs |
| Google Trends (pytrends) | Unlimited | Free |
| Twitter API | 1,500 tweets/mo | — |
| YouTube API | 10,000 units/day | — |
| **Total** | **~$0** | |

---

## Adding Platforms

### TikTok
Edit `publish_service.py` → `publish_tiktok()`. Requires TikTok for Developers business account approval.

### Instagram
Edit `publish_service.py` → `publish_instagram()`. Requires Meta Graph API + connected Facebook Page.

---

## Project Structure

```
app/
├── main.py                  # FastAPI app + lifespan
├── requirements.txt
├── Dockerfile
├── render.yaml
├── .env.example
├── services/
│   ├── trend_service.py     # Google Trends + seed fallback
│   ├── ai_service.py        # OpenAI content generation
│   ├── video_service.py     # gTTS + Pillow + FFmpeg
│   └── publish_service.py   # Twitter + YouTube + stubs
└── scheduler/
    └── cron_jobs.py         # APScheduler jobs
```
