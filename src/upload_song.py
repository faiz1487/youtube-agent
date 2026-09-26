"""
Publish Suno Audio Track to YouTube
====================================
This script takes an audio track (e.g. downloaded from Suno.com), uses Google Gemini
to generate an SEO title, tags, description, and aesthetic 16:9 thumbnail,
attaches the thumbnail to the audio, and uploads it to your YouTube channel.

Usage:
  python src/upload_song.py --audio "path/to/song.mp3" [--title "Custom Title"] [--privacy public]
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Ensure root is in sys.path
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PublishSunoAudio")

from src.config import validate_config, TEMP_DIR, OUTPUT_DIR, YOUTUBE_PRIVACY_STATUS
from src.lyrics_generator import generate_song_package
from src.cover_generator import generate_cover_art
from src.video_maker import create_music_video
from src.youtube_uploader import YouTubeUploader


def publish_audio_to_youtube(
    audio_path: Path,
    title: str = None,
    genre: str = None,
    privacy: str = None
):
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Validate YouTube credentials
    validate_config(dry_run=False)

    logger.info("=====================================================")
    logger.info("  PUBLISHING SUNO AUDIO TO YOUTUBE ('The Cover Booth')")
    logger.info(f"  Audio File: {audio_path.name}")
    logger.info("=====================================================")

    # Step 1: Use Gemini to generate viral title, description, tags & thumbnail design
    logger.info(">>> STEP 1: Generating YouTube metadata with Gemini...")
    inferred_genre = genre or "Original AI Music"
    metadata_pkg = generate_song_package(genre=inferred_genre, theme=title)

    song_title = title or metadata_pkg.get("title", audio_path.stem)
    description = metadata_pkg.get("description", f"Original song: {song_title}\n\n#music #originalsong")
    tags = metadata_pkg.get("tags", ["music", "original song", "ai music"])
    image_prompt = metadata_pkg.get("dalle_image_prompt", f"Cinematic album cover for {song_title}")

    logger.info(f"Video Title: {song_title}")

    # Step 2: Generate Aesthetic 16:9 Cover Thumbnail
    logger.info(">>> STEP 2: Creating 16:9 Cover Art Thumbnail...")
    thumbnail_path = TEMP_DIR / f"thumb_{int(audio_path.stat().st_mtime)}.png"
    generate_cover_art(
        title=song_title,
        genre=metadata_pkg.get("genre", inferred_genre),
        image_prompt=image_prompt,
        output_path=thumbnail_path
    )

    # Step 3: Combine Audio + Thumbnail into lightweight 1080p MP4 for YouTube
    logger.info(">>> STEP 3: Attaching Thumbnail to Audio (Creating MP4)...")
    safe_title = "".join(c for c in song_title if c.isalnum() or c in (" ", "_", "-")).strip()
    video_path = OUTPUT_DIR / f"{safe_title}.mp4"

    create_music_video(
        image_path=thumbnail_path,
        audio_path=audio_path,
        output_path=video_path,
        with_visualizer=True  # Renders smooth audio visualizer wave over thumbnail
    )

    # Step 4: Upload to YouTube channel
    privacy_status = privacy or YOUTUBE_PRIVACY_STATUS
    logger.info(f">>> STEP 4: Uploading to YouTube (Privacy: {privacy_status})...")
    uploader = YouTubeUploader()
    result = uploader.upload_video(
        video_path=video_path,
        title=song_title,
        description=description,
        tags=tags,
        thumbnail_path=thumbnail_path,
        privacy=privacy_status
    )

    logger.info("=====================================================")
    logger.info("            UPLOADED SUCCESSFULLY!                   ")
    logger.info(f"  Title: {result.get('title')}")
    logger.info(f"  Watch URL: {result.get('url')}")
    logger.info("=====================================================")
    return result


def main():
    parser = argparse.ArgumentParser(description="Upload Suno Audio with Gemini Thumbnail to YouTube")
    parser.add_argument("--audio", type=str, required=True, help="Path to the .mp3 or .wav audio file")
    parser.add_argument("--title", type=str, default=None, help="Song title (optional, Gemini will generate if omitted)")
    parser.add_argument("--genre", type=str, default=None, help="Musical genre (optional)")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default="public", help="YouTube privacy")

    args = parser.parse_args()

    audio_file = Path(args.audio).resolve()
    try:
        publish_audio_to_youtube(
            audio_path=audio_file,
            title=args.title,
            genre=args.genre,
            privacy=args.privacy
        )
    except Exception as e:
        logger.error(f"Failed to publish audio: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
