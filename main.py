"""
AI Social Media Content System
FastAPI backend — entry point
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
from scheduler.cron_jobs import scheduler, run_full_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup, shut it down on exit."""
    logger.info("Starting scheduler...")
    scheduler.start()
    yield
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="AI Social Media Content System",
    description="Automated trend detection, content generation & publishing",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Health ──────────────────────────────────────────────────────────────────


@app.get("/", tags=["Health"])
def root():
    return {"status": "running", "message": "AI Social Media Content System is live 🚀"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


# ── Manual triggers ──────────────────────────────────────────────────────────


@app.post("/run-pipeline", tags=["Pipeline"])
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger the full content pipeline."""
    background_tasks.add_task(run_full_pipeline)
    return {"message": "Pipeline started in background"}


@app.post("/run-trends", tags=["Pipeline"])
async def trigger_trends(background_tasks: BackgroundTasks):
    from services.trend_service import fetch_trends
    background_tasks.add_task(fetch_trends)
    return {"message": "Trend fetch started"}


@app.get("/scheduler/jobs", tags=["Scheduler"])
def list_jobs():
    jobs = [{"id": j.id, "next_run": str(j.next_run_time)} for j in scheduler.get_jobs()]
    return {"jobs": jobs}
