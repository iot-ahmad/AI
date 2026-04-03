"""
Publish Service
---------------
Handles publishing to:
  - Telegram Bot — الوسيلة الأساسية (مجانية 100%)
  - Twitter/X    — اختياري إذا توفرت credentials
  - (stub)       — TikTok / Instagram للمستقبل

Each publisher returns a dict: {"platform": str, "success": bool, "url": str}
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def publish_all(content: Dict, video_path: Optional[Path] = None) -> List[Dict]:
    """
    Publish to all configured platforms.
    Telegram is the primary channel — the video is sent as a file to your phone.
    Returns a list of publish results.
    """
    results = []

    # ── Telegram أولاً (مجاني، لا يحتاج موافقة) ──────────────────────────────
    if video_path and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        results.append(publish_telegram(content, video_path))
    elif video_path:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping Telegram")

    # ── Twitter اختياري ──────────────────────────────────────────────────────
    if os.getenv("TWITTER_API_KEY"):
        results.append(publish_twitter(content))

    if not results:
        logger.warning("No platform credentials configured. Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env")
        results.append({
            "platform": "none",
            "success": False,
            "url": "",
            "note": "No credentials found in .env",
        })

    return results


# ── Telegram Bot ──────────────────────────────────────────────────────────────


def publish_telegram(content: Dict, video_path: Path) -> Dict:
    """
    ترسل الفيديو كملف حقيقي (sendVideo) إلى هاتفك عبر التليجرام.
    بعدها تضغط Forward وتنشر بنفسك على أي منصة.
    """
    try:
        import requests

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        keyword = content.get("keyword", "")
        caption_parts = []
        if content.get("tiktok_caption"):
            caption_parts.append(content["tiktok_caption"])
        if content.get("hashtags"):
            tags = " ".join(f"#{h}" for h in content["hashtags"][:5])
            caption_parts.append(tags)

        caption = "\n\n".join(caption_parts)[:1024]  # Telegram limit

        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML",
            "supports_streaming": True,
        }

        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            response = requests.post(url, data=data, files=files, timeout=120)
            response.raise_for_status()

        logger.info("✅ Telegram: video sent to chat %s", chat_id)
        return {"platform": "telegram", "success": True, "url": f"tg://chat/{chat_id}"}

    except Exception as exc:
        logger.error("Telegram publish failed: %s", exc)
        return {"platform": "telegram", "success": False, "url": "", "error": str(exc)}


# ── Twitter (اختياري) ────────────────────────────────────────────────────────


def publish_twitter(content: Dict) -> Dict:
    """Post a tweet with caption + hashtags."""
    try:
        import tweepy

        client = tweepy.Client(
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_SECRET"),
        )

        caption = content.get("twitter_caption", content.get("hook", ""))
        tags = " ".join(f"#{h}" for h in content.get("hashtags", [])[:5])
        tweet_text = f"{caption}\n\n{tags}"[:280]

        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        url = f"https://twitter.com/i/web/status/{tweet_id}"
        logger.info("Tweeted: %s", url)
        return {"platform": "twitter", "success": True, "url": url}

    except Exception as exc:
        logger.error("Twitter publish failed: %s", exc)
        return {"platform": "twitter", "success": False, "url": "", "error": str(exc)}


# ── TikTok stub ───────────────────────────────────────────────────────────────


def publish_tiktok(content: Dict, video_path: Path) -> Dict:
    logger.info("TikTok publishing not yet configured (stub)")
    return {
        "platform": "tiktok",
        "success": False,
        "url": "",
        "note": "TikTok API requires business account approval",
    }


# ── Instagram stub ────────────────────────────────────────────────────────────


def publish_instagram(content: Dict, image_path: Optional[Path] = None) -> Dict:
    logger.info("Instagram publishing not yet configured (stub)")
    return {
        "platform": "instagram",
        "success": False,
        "url": "",
        "note": "Instagram requires Meta Graph API Business setup",
    }
