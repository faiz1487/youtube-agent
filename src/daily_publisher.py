"""
Daily Autonomous YouTube Music Publisher
=========================================
Runs daily via GitHub Actions cron schedule.
Workflow:
  1. Checks the `songs/` folder for any queued audio tracks (.mp3 / .wav).
  2. If found, picks the next unpublished track.
  3. Uses Google Gemini to generate viral SEO title, description, tags & 16:9 thumbnail.
  4. Renders a 1080p MP4 with animated audio visualizer waves using FFmpeg.
  5. Uploads the video + custom thumbnail to YouTube channel ('The Cover Booth').
  6. Records the published song in `published.json` so it never repeats.
  7. If `songs/` is empty, attempts live generation via Suno AI client.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Ensure project root is in sys.path
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("DailyPublisher")

from src.config import validate_config, TEMP_DIR, OUTPUT_DIR, YOUTUBE_PRIVACY_STATUS
from src.lyrics_generator import generate_song_package
from src.cover_generator import generate_cover_art
from src.video_maker import create_music_video
from src.youtube_uploader import YouTubeUploader

SONGS_DIR = ROOT_PATH / "songs"
PUBLISHED_LOG = ROOT_PATH / "published.json"
SONGS_DIR.mkdir(parents=True, exist_ok=True)


def load_published_history() -> dict:
    if PUBLISHED_LOG.exists():
        try:
            return json.loads(PUBLISHED_LOG.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Error reading {PUBLISHED_LOG}: {e}")
    return {"published_songs": []}


def save_published_history(history: dict):
    PUBLISHED_LOG.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Updated published history in {PUBLISHED_LOG}")


def get_next_queued_song() -> Path:
    """Finds the next audio file in songs/ that has not been published yet."""
    history = load_published_history()
    published_files = {item["filename"] for item in history.get("published_songs", [])}

    audio_extensions = {".mp3", ".wav", ".m4a", ".aac"}

    # Automatically discover and move any audio files accidentally uploaded to repository root
    try:
        for f in ROOT_PATH.iterdir():
            if f.is_file() and f.suffix.lower() in audio_extensions:
                target = SONGS_DIR / f.name
                if not target.exists():
                    logger.info(f"Discovered audio file '{f.name}' in repo root. Moving to songs/ folder.")
                    f.rename(target)
                elif f != target:
                    try:
                        f.unlink()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Error scanning repo root for audio files: {e}")

    queued_songs = sorted([
        f for f in SONGS_DIR.iterdir()
        if f.suffix.lower() in audio_extensions and f.name not in published_files
    ])

    if queued_songs:
        logger.info(f"Found {len(queued_songs)} queued song(s). Next to publish: {queued_songs[0].name}")
        return queued_songs[0]

    return None


def run_daily_publish():
    logger.info("=====================================================")
    logger.info("   DAILY AUTONOMOUS YOUTUBE MUSIC AGENT LAUNCHED    ")
    logger.info("=====================================================")

    # 1. Check for queued songs in songs/ folder
    next_song = get_next_queued_song()

    if next_song:
        logger.info(f"Processing queued track: {next_song.name}")
        raw_name = next_song.stem.replace("_", " ").strip()
        # Clean potential user prefixes like 'faizankaishar2_q35ev9_'
        if "_" in next_song.stem:
            raw_name = next_song.stem.split("_")[-1].strip()

        audio_file = next_song
        theme_hint = raw_name
    else:
        from src.config import SUNO_COOKIE, SUNO_API_URL, SUNO_API_KEY
        if not SUNO_COOKIE and not (SUNO_API_URL and SUNO_API_KEY):
            logger.error(
                "\n============================================================\n"
                "  QUEUE EMPTY & NO SUNO CREDENTIALS FOUND!\n"
                "============================================================\n"
                "  All tracks in the 'songs/' folder have already been published.\n"
                "  To continue automated daily publishing:\n"
                "    1. Upload your .mp3 audio songs to the 'songs/' folder on GitHub.\n"
                "    2. GitHub Actions will automatically take 1 song each day,\n"
                "       create the romantic couple thumbnail, and upload to YouTube!\n"
                "============================================================"
            )
            raise FileNotFoundError(
                "No queued songs remaining in 'songs/' directory and no Suno credentials provided."
            )

        logger.info("No queued songs found in songs/ folder. Attempting live generation via Suno...")
        from src.suno_client import SunoClient
        song_pkg = generate_song_package()
        title = song_pkg["title"]
        lyrics = song_pkg["lyrics"]
        suno_style = song_pkg["suno_style"]

        try:
            suno = SunoClient()
            audio_file = TEMP_DIR / "daily_generated_song.mp3"
            audio_file = suno.compose_song(
                title=title,
                style_tags=suno_style,
                lyrics=lyrics,
                output_path=audio_file
            )
            theme_hint = title
        except Exception as e:
            logger.error(
                f"\n============================================================\n"
                f"  Suno live generation failed: {e}\n"
                f"============================================================\n"
                f"  Note: Suno browser cookies expire quickly due to Cloudflare.\n"
                f"  RECOMMENDED: Upload .mp3 tracks directly to the 'songs/' folder on GitHub.\n"
                f"  The bot will automatically generate couple thumbnails and publish daily!\n"
                f"============================================================"
            )
            raise

    # 2. Generate YouTube metadata with Gemini
    logger.info(f">>> STEP 1: Generating SEO Title, Tags & Description with Gemini for: '{theme_hint}'...")
    metadata_pkg = generate_song_package(genre="Original AI Music", theme=theme_hint)

    song_title = theme_hint if theme_hint and len(theme_hint) > 3 else metadata_pkg.get("title", "New Song")
    description = metadata_pkg.get("description", f"Original song: {song_title}\n\n#music #originalsong")
    tags = metadata_pkg.get("tags", ["music", "original song", "ai music", "new release"])
    image_prompt = metadata_pkg.get("dalle_image_prompt", f"Cinematic visual album art for {song_title}")

    logger.info(f"Published Title: {song_title}")

    # 3. Generate 16:9 HD Cover Thumbnail
    logger.info(">>> STEP 2: Creating 16:9 Cover Thumbnail...")
    thumbnail_path = TEMP_DIR / f"thumb_{int(datetime.now().timestamp())}.png"
    generate_cover_art(
        title=song_title,
        genre=metadata_pkg.get("genre", "Original"),
        image_prompt=image_prompt,
        output_path=thumbnail_path
    )

    # 4. Render 1080p MP4 Video with Visualizer Wave
    logger.info(">>> STEP 3: Rendering 1080p MP4 Video with Audio Visualizer...")
    safe_title = "".join(c for c in song_title if c.isalnum() or c in (" ", "_", "-")).strip()
    video_path = OUTPUT_DIR / f"{safe_title}.mp4"

    create_music_video(
        image_path=thumbnail_path,
        audio_path=audio_file,
        output_path=video_path,
        with_visualizer=True
    )

    # 5. Upload to YouTube channel ('The Cover Booth')
    logger.info(f">>> STEP 4: Uploading to YouTube ('The Cover Booth') with Privacy: {YOUTUBE_PRIVACY_STATUS}...")
    uploader = YouTubeUploader()
    upload_res = uploader.upload_video(
        video_path=video_path,
        title=song_title,
        description=description,
        tags=tags,
        thumbnail_path=thumbnail_path,
        privacy=YOUTUBE_PRIVACY_STATUS
    )

    # 6. Record to published history
    history = load_published_history()
    history.setdefault("published_songs", []).append({
        "filename": audio_file.name,
        "title": song_title,
        "video_id": upload_res.get("video_id"),
        "url": upload_res.get("url"),
        "published_at": datetime.now().isoformat(),
        "privacy": upload_res.get("privacy")
    })
    save_published_history(history)

    logger.info("=====================================================")
    logger.info("      DAILY UPLOAD PUBLISHED SUCCESSFULLY!           ")
    logger.info(f" Track Title: {song_title}")
    logger.info(f" YouTube URL: {upload_res.get('url')}")
    logger.info("=====================================================")
    return upload_res


if __name__ == "__main__":
    try:
        run_daily_publish()
    except Exception as e:
        logger.error(f"Daily publish failed: {e}", exc_info=True)
        sys.exit(1)
