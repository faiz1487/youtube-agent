import os
import random
import logging
import urllib.parse
import requests
from pathlib import Path
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont

from src.config import (
    OPENAI_API_KEY,
    GENERATE_AI_COVER,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    TEMP_DIR,
    ROOT_DIR
)

logger = logging.getLogger(__name__)

ASSETS_FONTS_DIR = ROOT_DIR / "src" / "assets" / "fonts"


def get_font(font_type: str = "title", size: int = 72) -> ImageFont.ImageFont:
    """
    Load high quality font for Bollywood movie poster typography.
    Falls back gracefully across local assets, Windows, Linux, and PIL defaults.
    """
    candidates: List[Path] = []

    if font_type == "title":
        candidates.extend([
            ASSETS_FONTS_DIR / "CinematicTitle.ttf",
            Path("C:/Windows/Fonts/georgiab.ttf"),
            Path("C:/Windows/Fonts/palab.ttf"),
            Path("C:/Windows/Fonts/timesbd.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf")
        ])
    else:  # subtitle / presenter
        candidates.extend([
            ASSETS_FONTS_DIR / "Subtitle.ttf",
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
        ])

    for font_path in candidates:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size)
            except Exception:
                continue

    # Fallback to default system font
    try:
        return ImageFont.truetype("arial.ttf" if os.name == "nt" else "DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def format_title_lines(title: str) -> List[str]:
    """
    Format song title into 1 or 2 elegant lines for Bollywood movie poster layout.
    """
    words = title.strip().split()
    if len(words) <= 1:
        return [title.upper()]
    elif len(words) == 2:
        return [words[0].upper(), words[1].upper()]
    elif len(words) == 3:
        return [f"{words[0]} {words[1]}".upper(), words[2].upper()]
    elif len(words) == 4:
        return [f"{words[0]} {words[1]}".upper(), f"{words[2]} {words[3]}".upper()]
    else:
        mid = len(words) // 2
        return [" ".join(words[:mid]).upper(), " ".join(words[mid:]).upper()]


def apply_movie_poster_styling(
    base_image: Image.Image,
    title: str,
    subtitle: Optional[str] = None,
    presenter: str = "THE COVER BOOTH PRESENTS"
) -> Image.Image:
    """
    Applies cinematic Bollywood movie-poster gradient vignette and elegant typography.
    Leaves the couple on the right illuminated while ensuring the left title is crisp.
    """
    width, height = base_image.size
    im_rgba = base_image.convert("RGBA")

    # 1. Left-to-center dark gradient overlay
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)

    grad_extent = int(width * 0.6)  # Darkens left 60%
    for x in range(grad_extent):
        ratio = (grad_extent - x) / grad_extent
        alpha = int(220 * (ratio ** 1.5))
        grad_draw.line([(x, 0), (x, height)], fill=(10, 8, 18, alpha))

    # Subtle bottom vignette
    bottom_start = int(height * 0.78)
    for y in range(bottom_start, height):
        ratio = (y - bottom_start) / (height - bottom_start)
        alpha = int(140 * ratio)
        grad_draw.line([(0, y), (width, y)], fill=(8, 6, 14, alpha))

    composite = Image.alpha_composite(im_rgba, gradient)
    draw = ImageDraw.Draw(composite)

    # 2. Typography Setup
    lines = format_title_lines(title)
    max_line_len = max(len(l) for l in lines)

    if max_line_len > 18:
        title_font_size = 72
    elif max_line_len > 12:
        title_font_size = 84
    else:
        title_font_size = 94

    font_title = get_font("title", title_font_size)
    font_presenter = get_font("subtitle", 24)
    font_sub = get_font("subtitle", 26)

    margin_left = int(width * 0.065)  # ~125px on 1920
    start_y = int(height * 0.36)      # Vertically centered in upper-middle

    # Presenter Text (Golden accent)
    draw.text((margin_left, start_y), presenter.upper(), fill=(250, 190, 80, 240), font=font_presenter)

    # Multi-line Title with multi-layer deep drop shadow
    curr_y = start_y + 48
    line_bboxes = []
    for line in lines:
        for ox, oy, a in [(4, 4, 180), (3, 3, 210), (2, 2, 230)]:
            draw.text((margin_left + ox, curr_y + oy), line, fill=(0, 0, 0, a), font=font_title)
        draw.text((margin_left, curr_y), line, fill=(255, 255, 255, 255), font=font_title)
        bbox = draw.textbbox((margin_left, curr_y), line, font=font_title)
        line_bboxes.append(bbox)
        curr_y += (bbox[3] - bbox[1]) + 14

    # Golden decorative line
    max_text_width = max(b[2] - b[0] for b in line_bboxes) if line_bboxes else 400
    line_width = min(max(max_text_width, 350), 750)
    line_y = curr_y + 10
    draw.line([(margin_left, line_y), (margin_left + line_width, line_y)], fill=(250, 190, 80, 220), width=4)

    # Subtitle
    sub_text = (subtitle or "A JOURNEY OF TIMELESS LOVE • OFFICIAL MUSIC VIDEO").upper()
    draw.text((margin_left + 2, line_y + 26), sub_text, fill=(0, 0, 0, 200), font=font_sub)
    draw.text((margin_left, line_y + 24), sub_text, fill=(225, 225, 230, 240), font=font_sub)

    return composite.convert("RGB")


def generate_cover_art(
    title: str,
    genre: str = "Bollywood Romantic",
    image_prompt: str = "",
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate a 16:9 (1920x1080) cinematic Bollywood couple thumbnail/cover art.
    Uses Pollinations Flux (free) as primary, with automatic DALL-E & procedural fallbacks.
    """
    if output_path is None:
        output_path = TEMP_DIR / "cover_art.png"

    if GENERATE_AI_COVER:
        # Primary: Pollinations Flux Bollywood Couple Generator
        try:
            return _generate_pollinations_couple_cover(title, genre, image_prompt, output_path)
        except Exception as e:
            logger.warning(f"Pollinations couple cover generation failed: {e}. Checking secondary generators...")

        # Secondary: OpenAI DALL-E 3 (if key provided)
        if OPENAI_API_KEY:
            try:
                return _generate_dalle_cover(image_prompt or title, output_path, title=title)
            except Exception as e:
                logger.warning(f"DALL-E 3 cover generation failed: {e}.")

    # Fallback: Procedural stylized gradient
    return _generate_procedural_cover(title, genre, output_path)


ASSETS_IMAGES_DIR = ROOT_DIR / "src" / "assets" / "images"
DEFAULT_COUPLE_BG = ASSETS_IMAGES_DIR / "bollywood_couple_default.jpg"


def _generate_pollinations_couple_cover(
    title: str,
    genre: str,
    image_prompt: str,
    output_path: Path
) -> Path:
    """
    Generates a cinematic Bollywood romantic couple image via Pollinations AI.
    Uses 1024x576 for ultra-fast generation (<10s) and zero timeouts, then upscales to 1080p.
    Automatically fails over between Flux and Turbo models.
    """
    logger.info("Generating romantic Bollywood couple cover via Pollinations AI...")

    scenic_theme = (
        image_prompt.strip() if image_prompt and len(image_prompt.strip()) > 10
        else "majestic snow-capped mountain peaks and calm lake at golden hour sunset, glowing pink and amber sky, wildflowers"
    )

    couple_prompt = (
        f"Romantic Bollywood music video poster, medium shot handsome Indian man with styled beard "
        f"lovingly embracing beautiful young Indian woman in elegant pink lehenga, couple positioned on right side of frame, "
        f"{scenic_theme}, warm sunset golden hour lighting, glowing romantic atmosphere, 8k, ultra-detailed photorealistic portrait, sharp focus"
    )

    encoded_prompt = urllib.parse.quote(couple_prompt)
    seed = random.randint(100, 999999)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    # Try fast generation: Flux first, then Turbo
    models_to_try = ["flux", "turbo"]
    img_bytes = None

    for model in models_to_try:
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&model={model}&nologo=true&seed={seed}"
        logger.info(f"Requesting Pollinations image (model={model}, seed={seed})...")
        try:
            res = requests.get(url, headers=headers, timeout=35)
            if res.status_code == 200 and len(res.content) > 10000:
                # Verify valid image header
                if res.content.startswith(b'\xff\xd8') or res.content.startswith(b'\x89PNG') or res.content.startswith(b'RIFF'):
                    img_bytes = res.content
                    logger.info(f"Pollinations {model} image successfully fetched ({len(img_bytes)} bytes)")
                    break
            logger.warning(f"Pollinations {model} returned status {res.status_code} (len={len(res.content)})")
        except Exception as e:
            logger.warning(f"Pollinations {model} request failed: {e}")

    if not img_bytes:
        raise RuntimeError("All Pollinations models failed to generate valid image bytes.")

    temp_img_file = output_path.with_suffix(".tmp.png")
    with open(temp_img_file, "wb") as f:
        f.write(img_bytes)

    with Image.open(temp_img_file) as raw_img:
        w, h = raw_img.size
        # Crop bottom 22px to eliminate any watermark
        crop_h = max(h - 22, 100)
        im_clean = raw_img.crop((0, 0, w, crop_h))
        # Scale to 1920x1080 (Full HD)
        im_hd = im_clean.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        # Apply Bollywood movie poster typography
        final_thumb = apply_movie_poster_styling(im_hd, title=title)
        final_thumb.save(output_path, "PNG", quality=95)

    if temp_img_file.exists():
        temp_img_file.unlink()

    logger.info(f"Romantic couple cover art successfully created at: {output_path} ({VIDEO_WIDTH}x{VIDEO_HEIGHT})")
    return output_path


def _generate_dalle_cover(image_prompt: str, output_path: Path, title: str = "") -> Path:
    """
    Generate cover art using OpenAI DALL-E 3 with movie poster styling.
    """
    from openai import OpenAI
    logger.info("Generating cover image with DALL-E 3...")

    prompt = (
        f"Romantic Bollywood couple, handsome Indian man and beautiful Indian woman in pastel attire, "
        f"{image_prompt}. Couple on right side of frame, warm golden hour sunset, 16:9 cinematic wallpaper, 4K, no text."
    )

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    img_data = requests.get(image_url, timeout=60).content

    temp_img_file = output_path.with_suffix(".tmp.png")
    with open(temp_img_file, "wb") as f:
        f.write(img_data)

    with Image.open(temp_img_file) as raw_img:
        im_hd = raw_img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        final_thumb = apply_movie_poster_styling(im_hd, title=title or "ORIGINAL MUSIC")
        final_thumb.save(output_path, "PNG")

    if temp_img_file.exists():
        temp_img_file.unlink()

    logger.info(f"DALL-E cover art saved to {output_path}")
    return output_path


def _generate_procedural_cover(title: str, genre: str, output_path: Path) -> Path:
    """
    Fallback: Uses the bundled romantic Bollywood couple background template.
    Guarantees every video has a high-quality romantic couple thumbnail even if offline.
    """
    logger.info("Using bundled Bollywood Romantic Couple base template for cover art...")

    if DEFAULT_COUPLE_BG.exists():
        try:
            with Image.open(DEFAULT_COUPLE_BG) as base_img:
                im_hd = base_img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
                styled = apply_movie_poster_styling(im_hd, title=title, subtitle="A JOURNEY OF TIMELESS LOVE")
                styled.save(output_path, "PNG")
                logger.info(f"Bundled couple cover art saved to {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"Error reading bundled couple background: {e}")

    # Ultimate fallback: Warm golden sunset gradient (never retro purple)
    width, height = VIDEO_WIDTH, VIDEO_HEIGHT
    base = Image.new("RGB", (width, height), color=(25, 12, 18))
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        r = int(30 * (1 - ratio) + 120 * ratio)
        g = int(15 * (1 - ratio) + 40 * ratio)
        b = int(25 * (1 - ratio) + 60 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    styled = apply_movie_poster_styling(base, title=title, subtitle=f"• {genre.upper()} ORIGINAL •")
    styled.save(output_path, "PNG")
    logger.info(f"Warm sunset fallback cover art saved to {output_path}")
    return output_path
