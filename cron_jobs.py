"""
Cron Jobs — APScheduler
-----------------------
Schedules:
  - Full pipeline: every 6 hours (configurable via PIPELINE_INTERVAL_HOURS)
  - Trend refresh: every 12 hours

Run order inside pipeline:
  1. fetch_trends
  2. generate_content  (for top trend)
  3. create_video
  4. publish_all
"""

import os
import logging
from typing import List, Dict, Optional
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

PIPELINE_INTERVAL_HOURS = int(os.getenv("PIPELINE_INTERVAL_HOURS", "6"))
TREND_INTERVAL_HOURS = int(os.getenv("TREND_INTERVAL_HOURS", "12"))

scheduler = BackgroundScheduler(timezone="UTC")


def run_full_pipeline():
    """
    Full automated pipeline:
    Trends → AI content → Video → Publish
    """
    logger.info("=== Pipeline started ===")

    # 1. Trends
    from services.trend_service import fetch_trends
    trends = fetch_trends()
    if not trends:
        logger.warning("No trends found. Aborting pipeline.")
        return

    results = []
    # Process top 1 trend per run to conserve resources
    for trend in trends[:1]:
        logger.info("Processing trend: %s", trend["keyword"])

        # 2. Generate content
        from services.ai_service import generate_content
        content = generate_content(trend)
        if not content:
            logger.warning("Content generation failed for: %s", trend["keyword"])
            continue

        # 3. Create video
        from services.video_service import create_video
        video_path: Optional[Path] = create_video(content)

        # 4. Publish
        from services.publish_service import publish_all
        publish_results = publish_all(content, video_path)

        results.append({
            "trend": trend["keyword"],
            "content_generated": bool(content),
            "video_created": video_path is not None,
            "publish_results": publish_results,
        })
        logger.info("Result: %s", results[-1])

    logger.info("=== Pipeline complete. Processed %d trend(s) ===", len(results))
    return results


# ── Register jobs ─────────────────────────────────────────────────────────────

scheduler.add_job(
    run_full_pipeline,
    trigger=IntervalTrigger(hours=PIPELINE_INTERVAL_HOURS),
    id="full_pipeline",
    name="Full content pipeline",
    replace_existing=True,
    max_instances=1,
    misfire_grace_time=60 * 10,  # 10 min grace window
)
