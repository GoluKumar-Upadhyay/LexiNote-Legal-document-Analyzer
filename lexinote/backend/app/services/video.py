from __future__ import annotations

import re
import textwrap
import uuid
from pathlib import Path

from app.core.config import BASE_DIR, settings
from app.services.llm import llm

try:
    from moviepy.editor import ImageClip, concatenate_videoclips
except Exception:  # pragma: no cover
    ImageClip = None
    concatenate_videoclips = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None

GENERATED_DIR = BASE_DIR / "generated"
VIDEOS_DIR = GENERATED_DIR / "videos"
SLIDES_DIR = GENERATED_DIR / "slides"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
SLIDES_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_COLORS = ["#14315d", "#0f766e", "#2563eb", "#7c3aed", "#b45309", "#be185d"]


def video_runtime_available() -> bool:
    return bool(Image and ImageDraw and ImageFont and ImageClip and concatenate_videoclips)


def _load_font(size: int):
    if not ImageFont:
        return None
    for path in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def build_storyboard(summary_text: str, category: str, language: str) -> tuple[dict, str]:
    prompt = f"""
Return strict JSON only:
{{
  "title": "Short title",
  "slides": [
    {{"heading": "Short heading", "body": "1-2 sentence explanation", "accent": "#2563eb"}}
  ]
}}

Rules:
- Make 4 to 6 slides.
- Use simple public-friendly language.
- Match the requested language.

Category: {category}
Language: {language}
Text:
{summary_text[:6000]}
""".strip()
    try:
        text, provider = llm.generate(
            prompt,
            "You create short educational storyboards. Return JSON only.",
            max_tokens=1200,
            temperature=0.12,
        )
        import json

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON storyboard found.")
        return json.loads(match.group(0)), provider
    except Exception:
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", summary_text) if item.strip()]
        slides = []
        for index, sentence in enumerate(sentences[:4] or ["Document summary ready for review."], start=1):
            slides.append(
                {
                    "heading": f"Point {index}",
                    "body": sentence[:220],
                    "accent": VIDEO_COLORS[(index - 1) % len(VIDEO_COLORS)],
                }
            )
        return {"title": f"{category.title()} Summary", "slides": slides}, "heuristic"


def _create_slide(heading: str, body: str, accent: str, slide_number: int, total: int) -> Path:
    if not (Image and ImageDraw):
        raise RuntimeError("Pillow is unavailable.")
    image = Image.new("RGB", (settings.video_width, settings.video_height), color="#f8fafc")
    draw = ImageDraw.Draw(image)
    accent_color = accent if re.match(r"^#[0-9a-fA-F]{6}$", str(accent)) else VIDEO_COLORS[(slide_number - 1) % len(VIDEO_COLORS)]
    draw.rectangle([(0, 0), (settings.video_width, 86)], fill=accent_color)
    draw.rounded_rectangle([(54, 126), (settings.video_width - 54, settings.video_height - 80)], radius=28, fill="#ffffff", outline="#dbeafe", width=3)
    draw.text((80, 30), "LexiNote", fill="#ffffff", font=_load_font(24))
    draw.text((84, 176), heading[:72], fill="#0f172a", font=_load_font(42))
    wrapped = textwrap.fill(body[:500], width=56)
    draw.multiline_text((84, 268), wrapped, fill="#334155", font=_load_font(28), spacing=14)
    draw.text((settings.video_width - 170, settings.video_height - 54), f"{slide_number}/{total}", fill="#ffffff", font=_load_font(22))
    path = SLIDES_DIR / f"slide_{uuid.uuid4().hex[:10]}.png"
    image.save(path)
    return path


def generate_video(summary_text: str, category: str, language: str) -> dict:
    if not video_runtime_available():
        raise RuntimeError("Video runtime is unavailable. Install Pillow and moviepy.")
    storyboard, provider = build_storyboard(summary_text, category, language)
    slides = storyboard.get("slides", [])[:6]
    slide_paths = [
        _create_slide(slide.get("heading", f"Slide {index}"), slide.get("body", ""), slide.get("accent", VIDEO_COLORS[(index - 1) % len(VIDEO_COLORS)]), index, len(slides))
        for index, slide in enumerate(slides, start=1)
    ]
    clips = [ImageClip(str(path)).set_duration(settings.video_slide_seconds) for path in slide_paths]
    final_clip = concatenate_videoclips(clips, method="compose")
    output_path = VIDEOS_DIR / f"lexinote_{uuid.uuid4().hex[:12]}.mp4"
    final_clip.write_videofile(str(output_path), fps=24, codec="libx264", audio=False, verbose=False, logger=None)
    final_clip.close()
    for clip in clips:
        clip.close()
    return {
        "video_path": f"/api/files/videos/{output_path.name}",
        "storyboard": storyboard,
        "_meta": {"provider_used": provider, "slide_count": len(slides)},
    }
