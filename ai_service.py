"""
AI Content Generation Service
------------------------------
Uses Google Gemini API (gemini-1.5-flash) to generate:
  - hook, script, tiktok_caption, hashtags
  - باللهجة العربية بناءً على الدولة المختارة
"""

import os
import json
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# خريطة الدولة → اللهجة
_GEO_DIALECT = {
    "saudi_arabia": "السعودية (الخليجية)",
    "egypt": "المصرية",
    "jordan": "الأردنية",
}


def generate_content(trend: Dict) -> Optional[Dict]:
    """
    Generate viral content for a trending topic using Gemini.

    Returns:
        {
            "keyword": str,
            "niche": str,
            "hook": str,
            "script": str,
            "tiktok_caption": str,
            "twitter_caption": str,
            "hashtags": list[str],
        }
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — using mock content")
        return _mock_content(trend)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        keyword = trend.get("keyword", "تريند عام")
        geo = trend.get("geo", "egypt")
        dialect = _GEO_DIALECT.get(geo, "العربية الفصحى البيضاء")

        prompt = (
            f"اكتب محتوى فيديو قصير وجذاب عن الموضوع التالي: «{keyword}».\n"
            f"استخدم اللهجة {dialect} في الكتابة.\n\n"
            "أعطني المخرجات حصراً بتنسيق JSON صالح (بدون أي نص خارجه) يحتوي على الحقول التالية:\n"
            "{\n"
            '  "hook": "جملة افتتاحية مشوِّقة أقل من 15 كلمة",\n'
            '  "script": "سكريبت فيديو 10-25 ثانية (80 كلمة كحد أقصى)، ضع [PAUSE] بين الجمل",\n'
            '  "tiktok_caption": "كابشن تيك توك أقل من 100 حرف",\n'
            '  "twitter_caption": "تغريدة أقل من 240 حرف",\n'
            '  "hashtags": ["هاشتاق1", "هاشتاق2", "هاشتاق3", "هاشتاق4", "هاشتاق5"]\n'
            "}"
        )

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # تنظيف الـ markdown fences إذا أضافها الموديل
        clean = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(clean)

        data["keyword"] = keyword
        data["niche"] = trend.get("niche", "general")
        return data

    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON, falling back to mock")
        return _mock_content(trend)
    except Exception as exc:
        logger.error("Gemini error: %s", exc)
        return _mock_content(trend)


def _mock_content(trend: Dict) -> Dict:
    keyword = trend.get("keyword", "تطوير الذات")
    return {
        "keyword": keyword,
        "niche": trend.get("niche", "general"),
        "hook": f"السر الذي لا يخبرك أحد به عن {keyword}!",
        "script": (
            f"معظم الناس يعتقدون أن {keyword} أمر صعب. [PAUSE] "
            "لكن الحقيقة بسيطة جداً. [PAUSE] "
            "ابدأ بـ 5 دقائق كل يوم ولاحظ الفرق."
        ),
        "tiktok_caption": f"هذه المعلومة غيّرت حياتي عن {keyword} 🔥",
        "twitter_caption": (
            f"رأي غير شائع: {keyword} لا يحتاج موهبة، بل نظام. هذا هو نظامي 🧵"
        ),
        "hashtags": [keyword.replace(" ", ""), "تطوير_الذات", "محتوى_عربي", "تريند"],
    }
