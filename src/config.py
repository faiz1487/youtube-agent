import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from root directory if it exists
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Workspace and output directories
OUTPUT_DIR = ROOT_DIR / "output"
TEMP_DIR = ROOT_DIR / "temp"

# Ensure output & temp directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# AI Provider Settings (Gemini / OpenAI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
GENERATE_AI_COVER = os.getenv("GENERATE_AI_COVER", "false").lower() in ("true", "1", "yes")

# Suno AI Settings
SUNO_MODE = os.getenv("SUNO_MODE", "cookie").strip().lower()  # "cookie" or "api_gateway"
SUNO_COOKIE = os.getenv("SUNO_COOKIE", "").strip()
SUNO_API_URL = os.getenv("SUNO_API_URL", "").strip().rstrip("/")
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "").strip()

# YouTube Settings
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public").strip().lower()

# Video & Music Generation Settings
DEFAULT_GENRES = [
    "Synthwave",
    "Lo-Fi Chillhop",
    "Cyberpunk Melodic",
    "Epic Cinematic Orchestral",
    "Indie Dream Pop",
    "Acoustic Folk Ballad",
    "Future Bass",
    "Ambient Atmospheric",
    "Neo Soul",
    "Electro Swing"
]
raw_genres = os.getenv("MUSIC_GENRES", "")
MUSIC_GENRES = [g.strip() for g in raw_genres.split(",") if g.strip()] if raw_genres else DEFAULT_GENRES

VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1920"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1080"))


def validate_config(dry_run: bool = False):
    """
    Validate that essential environment variables are set before running the pipeline.
    """
    errors = []

    if not dry_run:
        if not GEMINI_API_KEY and not OPENAI_API_KEY:
            errors.append("Either GEMINI_API_KEY or OPENAI_API_KEY must be set for lyric generation.")

        if SUNO_MODE == "cookie" and not SUNO_COOKIE:
            errors.append("SUNO_COOKIE is required when SUNO_MODE='cookie'.")
        elif SUNO_MODE == "api_gateway" and not (SUNO_API_URL and SUNO_API_KEY):
            errors.append("SUNO_API_URL and SUNO_API_KEY are required when SUNO_MODE='api_gateway'.")

        if not YOUTUBE_CLIENT_ID:
            errors.append("YOUTUBE_CLIENT_ID is not set.")
        if not YOUTUBE_CLIENT_SECRET:
            errors.append("YOUTUBE_CLIENT_SECRET is not set.")
        if not YOUTUBE_REFRESH_TOKEN:
            errors.append("YOUTUBE_REFRESH_TOKEN is not set. Run 'python scripts/setup_youtube_oauth.py' first.")

    if errors:
        error_msg = "\n  - " + "\n  - ".join(errors)
        raise ValueError(
            f"Configuration validation failed with the following missing credentials:\n{error_msg}\n\n"
            f"Please update your .env file or set them in your GitHub Repository Secrets."
        )
