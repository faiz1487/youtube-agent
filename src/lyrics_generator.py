import json
import random
import logging
import requests
from typing import Dict, Any, Optional

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    MUSIC_GENRES
)

logger = logging.getLogger(__name__)


def generate_song_package(genre: Optional[str] = None, theme: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate song title, Suno musical style prompt, lyrics, visual prompt,
    and YouTube description/tags using Google Gemini or OpenAI.
    """
    selected_genre = genre or random.choice(MUSIC_GENRES)

    # 1. Try Gemini first if key is available
    if GEMINI_API_KEY:
        try:
            return _generate_with_gemini(selected_genre, theme)
        except Exception as e:
            logger.warning(f"Gemini lyric generation failed: {e}. Trying OpenAI fallback if available.")

    # 2. Try OpenAI if key is available
    if OPENAI_API_KEY:
        try:
            return _generate_with_openai(selected_genre, theme)
        except Exception as e:
            logger.warning(f"OpenAI lyric generation failed: {e}.")

    raise RuntimeError(
        "Could not generate song package. Ensure valid GEMINI_API_KEY or OPENAI_API_KEY is configured."
    )


def _generate_with_gemini(selected_genre: str, theme: Optional[str]) -> Dict[str, Any]:
    """Generate song package using Google Gemini API (Free tier supported)."""
    logger.info(f"Generating lyrics and song metadata via Google Gemini ({GEMINI_MODEL}). Genre: {selected_genre}")

    theme_instruction = f"Song Theme: {theme}" if theme else "Pick a captivating, emotionally resonant, or viral theme suited for this genre."

    prompt = f"""You are an elite hit music producer, lyricist, and viral YouTube strategist.
Your task is to create an original, catchy, high-engagement song package ready for Suno AI music composition and YouTube publication.

Genre: {selected_genre}
{theme_instruction}

Output ONLY a valid JSON object matching the following schema:
{{
  "title": "Song Title (Emotional, Catchy, Capitalized)",
  "genre": "{selected_genre}",
  "suno_style": "Detailed Suno style tags under 120 characters, e.g. '80s synthwave, punchy drums, melancholic female vocals, analog synth leads, 115 bpm'",
  "lyrics": "Structured song lyrics with meta tags [Verse 1], [Chorus], [Verse 2], [Chorus], [Bridge], [Guitar Solo], [Chorus], [Outro]. Make sure it is rhythmic, impactful, and contains memorable hooks.",
  "dalle_image_prompt": "Cinematic, artistic 16:9 wallpaper visual description representing the mood and theme. Specify high resolution, digital art or photography style, beautiful lighting, NO text in the image.",
  "description": "Engaging YouTube description including: song overview, complete lyrics with linebreaks, credits, timestamps, and 5-8 relevant hashtags like #synthwave #music #originalsong.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"]
}}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.8
        }
    }

    res = requests.post(url, json=payload, timeout=45)
    if res.status_code != 200:
        logger.error(f"Gemini API returned error: {res.status_code} - {res.text}")
        res.raise_for_status()

    data = res.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(raw_text)
    logger.info(f"Successfully generated song package with Gemini: '{result.get('title')}'")
    return result


def _generate_with_openai(selected_genre: str, theme: Optional[str]) -> Dict[str, Any]:
    """Generate song package using OpenAI ChatGPT."""
    from openai import OpenAI
    logger.info(f"Generating lyrics and song metadata via OpenAI ({OPENAI_MODEL}). Genre: {selected_genre}")

    system_prompt = (
        "You are an elite hit music producer, lyricist, and viral YouTube strategist. "
        "Your task is to create an original, catchy, high-engagement song package ready for "
        "Suno AI music composition and YouTube publication.\n\n"
        "You must output ONLY a valid JSON object matching the requested schema."
    )

    theme_instruction = f"Song Theme: {theme}" if theme else "Pick a captivating, emotionally resonant, or viral theme suited for this genre."

    user_prompt = f"""
Genre: {selected_genre}
{theme_instruction}

Create a complete song package with the following JSON format:
{{
  "title": "Song Title (Emotional, Catchy, Capitalized)",
  "genre": "{selected_genre}",
  "suno_style": "Detailed Suno style tags under 120 characters, e.g. '80s synthwave, punchy drums, melancholic female vocals, analog synth leads, 115 bpm'",
  "lyrics": "Structured song lyrics with meta tags [Verse 1], [Chorus], [Verse 2], [Chorus], [Bridge], [Guitar Solo], [Chorus], [Outro]. Make sure it is rhythmic, impactful, and contains memorable hooks.",
  "dalle_image_prompt": "Cinematic, artistic 16:9 wallpaper visual description representing the mood and theme. Specify high resolution, digital art or photography style, beautiful lighting, NO text in the image.",
  "description": "Engaging YouTube description including: song overview, complete lyrics with linebreaks, credits, timestamps, and 5-8 relevant hashtags like #synthwave #music #originalsong.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"]
}}
"""

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    raw_content = response.choices[0].message.content
    result = json.loads(raw_content)
    logger.info(f"Successfully generated song package with OpenAI: '{result.get('title')}'")
    return result


def generate_mock_song_package() -> Dict[str, Any]:
    """
    Returns a mock song package for dry runs and testing without using any API quota.
    """
    return {
        "title": "Neon Horizons (Midnight Drive)",
        "genre": "Synthwave",
        "suno_style": "80s retro synthwave, pulsing bassline, lush analog synth leads, dreamy male vocals, 112 bpm",
        "lyrics": """[Verse 1]
Empty highway under ultraviolet skies
Reflection of the dashboard burning in your eyes
The city skyline fades into the purple mist
Chasing down the memories of promises we missed

[Chorus]
Take me to the neon horizon
Where the midnight never ends
Speeding through the echoes of the wire
Can we start all over again?
Oh, the night is alive!

[Verse 2]
Streetlights flickering like a broken tape
Searching for an exit, looking for escape
Analog heart beating in a digital world
Signals drifting where the road unfurls

[Chorus]
Take me to the neon horizon
Where the midnight never ends
Speeding through the echoes of the wire
Can we start all over again?

[Bridge]
[Synth Solo]
Signal fades, but the rhythm remains
Electric fire running through our veins

[Outro]
Drive into the dark...
Neon horizon...
Fade away...""",
        "dalle_image_prompt": "Retro 80s synthwave sports car driving on a futuristic glowing neon highway towards a digital grid horizon with a giant cyberpunk sun, aesthetic purple and cyan vaporwave colors, cinematic lighting, ultra-detailed 4k concept art.",
        "description": "Stream 'Neon Horizons' - an original retro synthwave journey through midnight streets.\n\n"
                       "🎵 Music & Lyrics created with AI.\n"
                       "Subscribe for daily original songs!\n\n"
                       "#synthwave #retrowave #cyberpunk #originalsong #chillmusic",
        "tags": ["synthwave", "retrowave", "cyberpunk", "electronic music", "chillwave", "synth music", "night drive", "80s music"]
    }
