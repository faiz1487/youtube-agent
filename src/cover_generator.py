import logging
import requests
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from src.config import (
    OPENAI_API_KEY,
    GENERATE_AI_COVER,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    TEMP_DIR
)

logger = logging.getLogger(__name__)


def generate_cover_art(
    title: str,
    genre: str,
    image_prompt: str,
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate a 16:9 (1920x1080) cover art image for the YouTube video and thumbnail.
    Uses OpenAI DALL-E 3 if enabled, with automatic fallback to stylized Pillow procedural generation.
    """
    if output_path is None:
        output_path = TEMP_DIR / "cover_art.png"

    if GENERATE_AI_COVER and OPENAI_API_KEY:
        try:
            return _generate_dalle_cover(image_prompt, output_path)
        except Exception as e:
            logger.warning(f"DALL-E 3 generation failed or quota reached: {e}. Falling back to procedural cover art.")

    return _generate_procedural_cover(title, genre, output_path)


def _generate_dalle_cover(image_prompt: str, output_path: Path) -> Path:
    """
    Generate cover art using OpenAI DALL-E 3 (1792x1024 aspect ratio, scaled to 1920x1080).
    """
    from openai import OpenAI
    logger.info(f"Generating 16:9 cover image with DALL-E 3. Prompt: {image_prompt[:100]}...")

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"{image_prompt}. Cinematic 16:9 wallpaper, 4K render, vibrant lighting, highly detailed, no text, no watermark.",
        size="1792x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    logger.info(f"Downloading DALL-E 3 image from {image_url[:80]}...")

    img_data = requests.get(image_url, timeout=60).content
    temp_img_file = output_path.with_suffix(".tmp.png")
    with open(temp_img_file, "wb") as f:
        f.write(img_data)

    # Resize to exact 1920x1080
    with Image.open(temp_img_file) as im:
        im_resized = im.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        im_resized.save(output_path, "PNG")

    if temp_img_file.exists():
        temp_img_file.unlink()

    logger.info(f"DALL-E cover art saved to {output_path} ({VIDEO_WIDTH}x{VIDEO_HEIGHT})")
    return output_path


def _generate_procedural_cover(title: str, genre: str, output_path: Path) -> Path:
    """
    Procedurally creates a gradient background with stylish visual aesthetic and typography.
    Used as an immediate fallback or cost-saving mode.
    """
    logger.info("Creating procedural visual cover art with Pillow...")

    width, height = VIDEO_WIDTH, VIDEO_HEIGHT
    base = Image.new("RGB", (width, height), color=(15, 12, 35))
    draw = ImageDraw.Draw(base)

    # Draw smooth vertical-diagonal gradient
    for y in range(height):
        ratio = y / height
        # Gradient from deep violet/blue to warm magenta
        r = int(15 * (1 - ratio) + 80 * ratio)
        g = int(12 * (1 - ratio) + 20 * ratio)
        b = int(35 * (1 - ratio) + 90 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add artistic geometric grid lines
    grid_color = (120, 90, 220, 60)
    for x in range(0, width, 80):
        draw.line([(x, height // 2), (width // 2 + (x - width // 2) * 3, height)], fill=grid_color)
    for y in range(height // 2, height, 40):
        draw.line([(0, y), (width, y)], fill=grid_color)

    # Glowing center circle / sun
    sun_radius = 220
    sun_center = (width // 2, height // 2 - 40)
    for i in range(sun_radius, 0, -5):
        alpha_ratio = (sun_radius - i) / sun_radius
        sr = int(255 * alpha_ratio + 120 * (1 - alpha_ratio))
        sg = int(80 * alpha_ratio + 30 * (1 - alpha_ratio))
        sb = int(140 * alpha_ratio + 180 * (1 - alpha_ratio))
        draw.ellipse(
            [
                sun_center[0] - i, sun_center[1] - i,
                sun_center[0] + i, sun_center[1] + i
            ],
            outline=(sr, sg, sb),
            width=2
        )

    # Text overlay
    try:
        font_title = ImageFont.truetype("arial.ttf", 64)
        font_sub = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw title
    title_text = title.upper()
    genre_text = f"• {genre.upper()} ORIGINAL •"

    # Title shadow and text
    draw.text((width // 2 + 3, height - 197), title_text, fill=(0, 0, 0), font=font_title, anchor="ms")
    draw.text((width // 2, height - 200), title_text, fill=(255, 255, 255), font=font_title, anchor="ms")

    # Genre subtitle
    draw.text((width // 2 + 2, height - 138), genre_text, fill=(0, 0, 0), font=font_sub, anchor="ms")
    draw.text((width // 2, height - 140), genre_text, fill=(255, 170, 80), font=font_sub, anchor="ms")

    base.save(output_path, "PNG")
    logger.info(f"Procedural cover art saved to {output_path}")
    return output_path
