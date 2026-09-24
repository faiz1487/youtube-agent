import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional

from src.config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> Optional[str]:
    """Check if ffmpeg executable is available on system PATH or via imageio_ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def create_music_video(
    image_path: Path,
    audio_path: Path,
    output_path: Optional[Path] = None,
    with_visualizer: bool = True
) -> Path:
    """
    Renders an MP4 video (1920x1080) combining the cover image and audio track.
    Includes an animated audio visualizer waveform across the bottom.
    """
    ffmpeg_exe = get_ffmpeg_path()
    if not ffmpeg_exe:
        raise RuntimeError(
            "FFmpeg is not installed or not found. "
            "Please install ffmpeg or run 'pip install imageio-ffmpeg'."
        )

    if output_path is None:
        output_path = OUTPUT_DIR / f"final_music_video_{int(audio_path.stat().st_mtime)}.mp4"

    logger.info(f"Rendering music video from:\n  Audio: {audio_path}\n  Image: {image_path}\n  Output: {output_path}")

    # Visualizer filter:
    # 1. Takes audio stream [1:a], renders wave visualizer with cyan/magenta tint at 1920x220
    # 2. Overlays waveform onto the cover image near the bottom
    filter_complex = (
        f"[1:a]showwaves=s={VIDEO_WIDTH}x220:mode=cline:colors=0x00ffff@0.85|0xff00ff@0.85:scale=cbrt[waves];"
        f"[0:v][waves]overlay=0:{VIDEO_HEIGHT}-260:format=auto[outv]"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", str(image_path),
        "-i", str(audio_path),
    ]

    if with_visualizer:
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "1:a",
        ])
    else:
        cmd.extend([
            "-map", "0:v",
            "-map", "1:a",
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-shortest",
        str(output_path)
    ])

    logger.info("Executing FFmpeg encoding...")
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if process.returncode != 0:
        logger.warning(f"FFmpeg with visualizer failed: {process.stderr[-400:]}. Retrying standard static video...")
        # Fallback to standard static still image if advanced filter failed
        fallback_cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "320k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path)
        ]
        fb_process = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if fb_process.returncode != 0:
            logger.error(f"FFmpeg fallback failed: {fb_process.stderr}")
            raise RuntimeError(f"FFmpeg video encoding failed: {fb_process.stderr[-500:]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Video file was not created or has 0 bytes.")

    logger.info(f"Video created successfully: {output_path} ({output_path.stat().st_size / (1024*1024):.2f} MB)")
    return output_path
