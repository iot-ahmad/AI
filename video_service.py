"""
Video Generation Service
-------------------------
Generates a vertical 9:16 short-form video from content data.
Supports Arabic text via arabic_reshaper + python-bidi.

Pipeline:
  1. gTTS  → voiceover.mp3  (lang=ar)
  2. Pillow → background image with hook text overlay (Arabic-safe)
  3. FFmpeg → combine image + audio → video.mp4
  4. FFmpeg → burn subtitle .srt → final.mp4

Output: /tmp/output/<keyword>/final.mp4
"""

import os
import re
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Video dimensions (9:16 vertical)
WIDTH = 1080
HEIGHT = 1920
FONT_SIZE = 60
OUTPUT_BASE = Path(os.getenv("OUTPUT_DIR", "/tmp/output"))

# Background colour palette — randomly picked per video
BG_COLOURS = [
    "#0f0f0f",  # near-black
    "#1a1a2e",  # deep navy
    "#16213e",  # dark blue
    "#0d3b66",  # ocean
    "#1b1b2f",  # indigo dark
]


def create_video(content: Dict) -> Optional[Path]:
    """
    Create a short-form video from AI-generated content.

    Returns path to final.mp4 or None on failure.
    """
    keyword = re.sub(r"[^\w]", "_", content.get("keyword", "video"))
    out_dir = OUTPUT_BASE / keyword
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        audio_path = _generate_voiceover(content["script"], out_dir)
        image_path = _generate_background(content, out_dir)
        raw_video = _combine_image_audio(image_path, audio_path, out_dir)
        final_video = _burn_subtitles(content["script"], raw_video, out_dir)
        logger.info("Video ready: %s", final_video)
        return final_video
    except Exception as exc:
        logger.error("Video creation failed: %s", exc)
        return None


# ── Arabic text helpers ────────────────────────────────────────────────────────


def _process_arabic_text(text: str) -> str:
    """
    معالجة النص العربي لعرضه بشكل صحيح في Pillow:
    1. arabic_reshaper  → يوصّل الحروف بعضها ببعض
    2. python-bidi      → يعكس اتجاه النص من اليمين لليسار
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        logger.warning("arabic_reshaper/bidi not installed — text may appear broken")
        return text


# ── Step 1: Voiceover ─────────────────────────────────────────────────────────


def _generate_voiceover(script: str, out_dir: Path) -> Path:
    from gtts import gTTS

    # Strip [PAUSE] cues before TTS
    clean_script = re.sub(r"\[PAUSE\]", "،", script)
    tts = gTTS(text=clean_script, lang="ar", slow=False)
    path = out_dir / "voiceover.mp3"
    tts.save(str(path))
    logger.info("Voiceover saved: %s", path)
    return path


# ── Step 2: Background image ──────────────────────────────────────────────────


def _generate_background(content: Dict, out_dir: Path) -> Path:
    from PIL import Image, ImageDraw
    import random

    bg_colour = random.choice(BG_COLOURS)
    img = Image.new("RGB", (WIDTH, HEIGHT), color=bg_colour)
    draw = ImageDraw.Draw(img)

    font_hook = _load_font(FONT_SIZE)
    font_sub = _load_font(36)

    hook = content.get("hook", "")
    niche = content.get("niche", "")

    # Niche tag (no Arabic reshaping needed for single tag)
    niche_display = _process_arabic_text(f"#{niche}") if niche else ""
    draw.text((WIDTH // 2, 200), niche_display, font=font_sub,
              fill="#ffffff", anchor="mm")

    # Hook text — معالجة عربية كاملة
    _draw_wrapped_text(draw, hook, font_hook, (WIDTH // 2, HEIGHT // 2 - 100),
                       fill="#ffffff", max_width=900)

    # CTA
    cta = _process_arabic_text("تابعنا لمزيد من المحتوى 🔥")
    draw.text((WIDTH // 2, HEIGHT - 250), cta, font=font_sub,
              fill="#cccccc", anchor="mm")

    path = out_dir / "background.jpg"
    img.save(str(path), quality=95)
    return path


def _load_font(size: int):
    from PIL import ImageFont

    # الأولوية: خط ناكولا (عربي) ← ثم ديجافو كـ fallback
    candidates = [
        "/usr/share/fonts/truetype/nakula/nakula.ttf",      # fonts-nakula (Debian)
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",  # noto arabic
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_wrapped_text(draw, text: str, font, center, fill, max_width: int):
    """رسم نص عربي معالَج مع تغليف تلقائي للأسطر."""
    # معالجة النص العربي أولاً
    processed = _process_arabic_text(text)

    words = processed.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        try:
            bbox = font.getbbox(test)
            width = bbox[2] - bbox[0]
        except Exception:
            width = len(test) * (FONT_SIZE // 2)  # تقدير fallback

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = center
    try:
        line_h = font.size + 10
    except Exception:
        line_h = FONT_SIZE + 10

    y -= (len(lines) * line_h) // 2
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill, anchor="mm")
        y += line_h


# ── Step 3: Combine image + audio ────────────────────────────────────────────


def _combine_image_audio(image: Path, audio: Path, out_dir: Path) -> Path:
    output = out_dir / "raw_video.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        str(output),
    ]
    _run(cmd)
    return output


# ── Step 4: Burn subtitles ────────────────────────────────────────────────────


def _burn_subtitles(script: str, video: Path, out_dir: Path) -> Path:
    srt_path = _write_srt(script, out_dir)
    output = out_dir / "final.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vf", (
            f"subtitles={srt_path}:force_style="
            f"'FontSize=28,PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,Outline=2,Alignment=2'"
        ),
        "-c:a", "copy",
        str(output),
    ]
    try:
        _run(cmd)
        return output
    except Exception:
        logger.warning("Subtitle burn failed — using raw video")
        return video


def _write_srt(script: str, out_dir: Path) -> Path:
    sentences = re.split(r"[\.!\?،]|\[PAUSE\]", script)
    sentences = [s.strip() for s in sentences if s.strip()]

    srt_lines = []
    time_per = 4  # seconds per sentence estimate
    for i, sentence in enumerate(sentences):
        start = _srt_time(i * time_per)
        end = _srt_time((i + 1) * time_per)
        srt_lines.append(f"{i + 1}\n{start} --> {end}\n{sentence}\n")

    srt_path = out_dir / "subtitles.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return srt_path


def _srt_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d},000"


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{result.stderr[-500:]}")
