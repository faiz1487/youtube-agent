import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path

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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("YouTubeDailyMusicBot")

from src.config import validate_config, TEMP_DIR, OUTPUT_DIR
from src.lyrics_generator import generate_song_package, generate_mock_song_package
from src.suno_client import SunoClient
from src.cover_generator import generate_cover_art
from src.video_maker import create_music_video
from src.youtube_uploader import YouTubeUploader


def run_pipeline(
    dry_run: bool = False,
    skip_upload: bool = False,
    genre: str = None,
    theme: str = None,
    privacy: str = None
):
    """
    Executes the daily automated music production & YouTube publishing pipeline.
    """
    logger.info("=====================================================")
    logger.info("  DAILY YOUTUBE AI MUSIC AGENT - PIPELINE STARTED   ")
    logger.info("=====================================================")

    # 1. Validate environment configuration
    validate_config(dry_run=dry_run)

    # 2. Step 1: Generate Song Concept, Lyrics & Metadata
    logger.info(">>> STEP 1: Generating Lyrics & Concept with ChatGPT...")
    if dry_run:
        logger.info("[Dry Run] Using mock song package.")
        song_pkg = generate_mock_song_package()
    else:
        song_pkg = generate_song_package(genre=genre, theme=theme)

    title = song_pkg["title"]
    lyrics = song_pkg["lyrics"]
    suno_style = song_pkg["suno_style"]
    image_prompt = song_pkg["dalle_image_prompt"]
    description = song_pkg["description"]
    tags = song_pkg.get("tags", [])
    selected_genre = song_pkg.get("genre", "Original")

    logger.info(f"Song Title: {title}")
    logger.info(f"Suno Style Tags: {suno_style}")

    # 3. Step 2: Compose Music with Suno AI
    logger.info(">>> STEP 2: Composing Music via Suno AI...")
    audio_file = TEMP_DIR / f"song_{int(Path().stat().st_mtime if hasattr(Path(), 'stat') else 1)}.mp3"

    if dry_run:
        # In dry run mode, check if a dummy audio file can be synthesized or used
        logger.info("[Dry Run] Generating synthetic audio tone for testing...")
        from src.video_maker import get_ffmpeg_path
        ffmpeg_exe = get_ffmpeg_path()
        if ffmpeg_exe:
            subprocess.run(
                [ffmpeg_exe, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-c:a", "libmp3lame", "-b:a", "192k", str(audio_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        if not audio_file.exists():
            # Minimal dummy fallback
            audio_file.write_bytes(b"DUMMY AUDIO DATA")
    else:
        suno = SunoClient()
        audio_file = suno.compose_song(
            title=title,
            style_tags=suno_style,
            lyrics=lyrics,
            output_path=audio_file
        )

    # 4. Step 3: Generate 16:9 Cover Art & Thumbnail
    logger.info(">>> STEP 3: Generating Visuals & Thumbnail...")
    cover_image_path = TEMP_DIR / "cover_art.png"
    if dry_run:
        from src.cover_generator import _generate_procedural_cover
        _generate_procedural_cover(title, selected_genre, cover_image_path)
    else:
        generate_cover_art(
            title=title,
            genre=selected_genre,
            image_prompt=image_prompt,
            output_path=cover_image_path
        )

    # 5. Step 4: Render MP4 Video with FFmpeg Audio Visualizer
    logger.info(">>> STEP 4: Rendering 1080p MP4 Video with Visualizer...")
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()
    final_video_path = OUTPUT_DIR / f"{safe_title}.mp4"

    video_path = create_music_video(
        image_path=cover_image_path,
        audio_path=audio_file,
        output_path=final_video_path,
        with_visualizer=True
    )

    # 6. Step 5: Upload to YouTube
    if dry_run or skip_upload:
        logger.info(f"[Dry Run / Skip Upload] Video successfully rendered at: {video_path}")
        logger.info("Skipping YouTube upload step.")
        upload_result = {
            "video_id": "DRY_RUN_MOCK_ID",
            "url": "https://youtu.be/mock_id",
            "title": title,
            "privacy": privacy or "dry_run"
        }
    else:
        logger.info(">>> STEP 5: Uploading Video & Thumbnail to YouTube...")
        uploader = YouTubeUploader()
        upload_result = uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            thumbnail_path=cover_image_path,
            privacy=privacy
        )

    logger.info("=====================================================")
    logger.info("            MISSION COMPLETED SUCCESSFULLY!          ")
    logger.info(f" Track Title: {title}")
    logger.info(f" Video Path:  {video_path}")
    logger.info(f" YouTube URL: {upload_result.get('url')}")
    logger.info("=====================================================")

    return upload_result


def main():
    parser = argparse.ArgumentParser(description="Automated Daily YouTube Music Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run with mock data without using paid API quotas or uploading.")
    parser.add_argument("--skip-upload", action="store_true", help="Run generation and video rendering, but do not upload to YouTube.")
    parser.add_argument("--genre", type=str, default=None, help="Force a specific musical genre.")
    parser.add_argument("--theme", type=str, default=None, help="Provide a custom song theme or story.")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default=None, help="Override YouTube privacy status.")

    args = parser.parse_args()

    try:
        run_pipeline(
            dry_run=args.dry_run,
            skip_upload=args.skip_upload,
            genre=args.genre,
            theme=args.theme,
            privacy=args.privacy
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
