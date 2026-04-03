"""
Trend Detection Service
-----------------------
Fetches trending topics via pytrends (Google Trends — free, no API key).
Targets Arabic markets: Saudi Arabia and Egypt.
Falls back to a curated Arabic seed list when the API is rate-limited.
"""

import os
import logging
import random
from typing import List, Dict

logger = logging.getLogger(__name__)

# ── Configurable niche keywords ──────────────────────────────────────────────
NICHE_KEYWORDS: List[str] = [
    kw.strip()
    for kw in os.getenv(
        "NICHE_KEYWORDS",
        "AI,تقنية,أعمال,تطوير الذات,استثمار,ريادة الأعمال",
    ).split(",")
]

# ── القائمة الاحتياطية بمواضيع عربية رائجة ──────────────────────────────────
SEED_TRENDS: List[Dict] = [
    {"keyword": "تقنيات الذكاء الاصطناعي", "niche": "AI", "score": 95},
    {"keyword": "ريادة الأعمال للشباب", "niche": "أعمال", "score": 90},
    {"keyword": "الروتين الصباحي", "niche": "تطوير الذات", "score": 85},
    {"keyword": "أدوات الذكاء الاصطناعي للطلاب", "niche": "AI", "score": 83},
    {"keyword": "كيف تركز وتنجز", "niche": "تطوير الذات", "score": 80},
    {"keyword": "أفكار مشاريع مربحة", "niche": "أعمال", "score": 88},
    {"keyword": "استثمار 100 دولار", "niche": "استثمار", "score": 82},
    {"keyword": "ChatGPT للعمل الحر", "niche": "AI", "score": 87},
]

# ── الدول المستهدفة (صيغة pytrends) ─────────────────────────────────────────
DEFAULT_GEO_LIST = ["saudi_arabia", "egypt"]


def fetch_trends(geo_list: List[str] = None, top_n: int = 5) -> List[Dict]:
    """
    Fetch trending topics.

    يختار دولة عشوائياً من القائمة في كل تشغيل.

    Returns a list of dicts:
        [{"keyword": "...", "niche": "...", "score": int, "geo": str}, ...]
    """
    if geo_list is None:
        geo_list = DEFAULT_GEO_LIST

    geo = random.choice(geo_list)
    logger.info("Fetching trends for: %s", geo)

    trends = _fetch_from_google_trends(geo, top_n)

    if not trends:
        logger.warning("Google Trends unavailable — using Arabic seed topics")
        trends = _sample_seed_trends(top_n)

    # إضافة الدولة لكل ترند لاستخدامها في اختيار اللهجة
    for t in trends:
        t.setdefault("geo", geo)

    trends = _filter_by_niche(trends)
    logger.info("Trends selected: %s", [t["keyword"] for t in trends])
    return trends


# ── Internal helpers ─────────────────────────────────────────────────────────


def _fetch_from_google_trends(geo: str, top_n: int) -> List[Dict]:
    try:
        from pytrends.request import TrendReq

        # hl=ar-SA للحصول على نتائج عربية دقيقة
        pytrends = TrendReq(hl="ar-SA", tz=180, timeout=(10, 25))
        df = pytrends.trending_searches(pn=geo.lower())
        keywords = df[0].tolist()[:top_n]
        return [
            {"keyword": kw, "niche": _guess_niche(kw), "score": 100 - i * 5, "geo": geo}
            for i, kw in enumerate(keywords)
        ]
    except Exception as exc:
        logger.warning("pytrends error: %s", exc)
        return []


def _sample_seed_trends(top_n: int) -> List[Dict]:
    sampled = random.sample(SEED_TRENDS, min(top_n, len(SEED_TRENDS)))
    return sorted(sampled, key=lambda x: x["score"], reverse=True)


def _filter_by_niche(trends: List[Dict]) -> List[Dict]:
    if not NICHE_KEYWORDS:
        return trends
    filtered = [
        t for t in trends
        if t.get("niche", "").lower() in [n.lower() for n in NICHE_KEYWORDS]
    ]
    return filtered or trends  # fall back to all if nothing matches


def _guess_niche(keyword: str) -> str:
    kw = keyword.lower()
    mapping = {
        "AI": ["ai", "gpt", "chatgpt", "openai", "ذكاء", "تقنية", "llm"],
        "أعمال": ["business", "startup", "ريادة", "مشروع", "أعمال", "hustle"],
        "تطوير الذات": ["motivation", "روتين", "تطوير", "عادات", "mindset", "نجاح"],
        "استثمار": ["invest", "استثمار", "مال", "finance", "crypto", "سهم"],
    }
    for niche, terms in mapping.items():
        if any(t in kw for t in terms):
            return niche
    return "general"
