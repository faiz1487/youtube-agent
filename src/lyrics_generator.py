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

GEMINI_FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.8-flash"
]


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
    """Generate song package using Google Gemini API with automatic model failover."""
    theme_instruction = f"Song Theme: {theme}" if theme else "Pick a captivating, emotionally resonant, or viral theme suited for this genre."

    prompt = f"""You are an elite hit Bollywood music producer, lyricist, and viral YouTube strategist.
Your task is to create an original, deeply emotional, catchy romantic song package (Hindi/Bollywood romantic ballad) ready for Suno AI music composition and YouTube publication.

Genre: {selected_genre}
{theme_instruction}

Output ONLY a valid JSON object matching the following schema:
{{
  "title": "Song Title (Emotional, Romantic, Capitalized, e.g. 'Humhari Dastaan', 'Adhoora Dil', 'Tere Bina')",
  "genre": "{selected_genre}",
  "suno_style": "Detailed Suno style tags under 120 characters, e.g. 'Bollywood romantic ballad, soulful acoustic guitar, warm male vocals, lush strings, 85 bpm'",
  "lyrics": "Structured romantic song lyrics in beautiful Hindi/Hinglish with meta tags [Verse 1], [Chorus], [Verse 2], [Chorus], [Bridge], [Chorus], [Outro]. Make sure it is deeply emotional, poetic, and contains unforgettable romantic hooks.",
  "dalle_image_prompt": "Scenic backdrop description for a romantic Bollywood couple poster, e.g. 'majestic snow-capped Himalayan mountains at sunset with alpine lake and wildflowers' or 'tranquil lake at golden hour sunset with glowing warm pink sky'. Specify scenic landscape and warm romantic lighting, NO text.",
  "description": "Engaging YouTube description including: song overview, complete lyrics with linebreaks, credits for 'The Cover Booth', and 5-8 relevant hashtags like #bollywood #romanticsong #hindisong #thecoverbooth.",
  "tags": ["bollywood romantic", "hindi song", "love song", "soulful ballad", "the cover booth", "new hindi song", "acoustic love", "romantic music"]
}}
"""

    models_to_try = [GEMINI_MODEL] if GEMINI_MODEL else []
    for m in GEMINI_FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

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

    last_error = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        logger.info(f"Attempting lyric generation with Gemini ({model_name}). Genre: {selected_genre}")
        try:
            res = requests.post(url, json=payload, timeout=35)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Clean potential markdown fences
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```"):
                    lines = cleaned_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    cleaned_text = "\n".join(lines).strip()

                result = json.loads(cleaned_text)
                logger.info(f"Successfully generated song package with Gemini ({model_name}): '{result.get('title')}'")
                return result
            else:
                logger.warning(f"Gemini {model_name} returned status {res.status_code}: {res.text[:100]}")
                last_error = f"{res.status_code} - {res.text[:100]}"
        except Exception as err:
            logger.warning(f"Error calling Gemini ({model_name}): {err}")
            last_error = err

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def _generate_with_openai(selected_genre: str, theme: Optional[str]) -> Dict[str, Any]:
    """Generate song package using OpenAI ChatGPT."""
    from openai import OpenAI
    logger.info(f"Generating lyrics and song metadata via OpenAI ({OPENAI_MODEL}). Genre: {selected_genre}")

    system_prompt = (
        "You are an elite hit Bollywood music producer, lyricist, and viral YouTube strategist. "
        "Your task is to create an original, deeply emotional romantic song package (Hindi/Bollywood romantic ballad) ready for "
        "Suno AI music composition and YouTube publication.\n\n"
        "You must output ONLY a valid JSON object matching the requested schema."
    )

    theme_instruction = f"Song Theme: {theme}" if theme else "Pick a captivating, emotionally resonant, or viral theme suited for this genre."

    user_prompt = f"""
Genre: {selected_genre}
{theme_instruction}

Create a complete song package with the following JSON format:
{{
  "title": "Song Title (Emotional, Romantic, Capitalized, e.g. 'Humhari Dastaan', 'Adhoora Dil', 'Tere Bina')",
  "genre": "{selected_genre}",
  "suno_style": "Detailed Suno style tags under 120 characters, e.g. 'Bollywood romantic ballad, soulful acoustic guitar, warm male vocals, lush strings, 85 bpm'",
  "lyrics": "Structured romantic song lyrics in beautiful Hindi/Hinglish with meta tags [Verse 1], [Chorus], [Verse 2], [Chorus], [Bridge], [Chorus], [Outro]. Make sure it is deeply emotional, poetic, and contains unforgettable romantic hooks.",
  "dalle_image_prompt": "Scenic backdrop description for a romantic Bollywood couple poster, e.g. 'majestic snow-capped Himalayan mountains at sunset with alpine lake and wildflowers' or 'tranquil lake at golden hour sunset with glowing warm pink sky'. Specify scenic landscape and warm romantic lighting, NO text.",
  "description": "Engaging YouTube description including: song overview, complete lyrics with linebreaks, credits for 'The Cover Booth', and 5-8 relevant hashtags like #bollywood #romanticsong #hindisong #thecoverbooth.",
  "tags": ["bollywood romantic", "hindi song", "love song", "soulful ballad", "the cover booth", "new hindi song", "acoustic love", "romantic music"]
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
