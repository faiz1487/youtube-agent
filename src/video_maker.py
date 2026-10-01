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
    with_visualizer: bool = False
) -> Path:
    """
    Renders a Full HD MP4 video (1920x1080) combining the exact cover thumbnail image and audio track.
    Guarantees visually lossless 1080p quality matching the thumbnail image throughout the entire video.
    """
    ffmpeg_exe = get_ffmpeg_path()
    if not ffmpeg_exe:
        raise RuntimeError(
            "FFmpeg is not installed or not found. "
            "Please install ffmpeg or run 'pip install imageio-ffmpeg'."
        )

    if output_path is None:
        output_path = OUTPUT_DIR / f"final_music_video_{int(audio_path.stat().st_mtime)}.mp4"

    logger.info(f"Rendering Full HD 1080p music video:\n  Audio: {audio_path}\n  Thumbnail/Cover: {image_path}\n  Output: {output_path}")

    if with_visualizer:
        # Subtle, elegant golden/white waveform along the lower third (does not obstruct couple or title)
        filter_complex = (
            f"[1:a]showwaves=s={VIDEO_WIDTH}x80:mode=cline:colors=0xf5c060@0.75|0xffffff@0.55:scale=cbrt[waves];"
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,format=yuv420p[base];"
            f"[base][waves]overlay=0:{VIDEO_HEIGHT}-110:format=auto[outv]"
        )
        cmd = [
            ffmpeg_exe,
            "-y",
            "-loop", "1",
            "-framerate", "30",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",
            "-pix_fmt", "yuv420p",
            "-color_range", "1",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-c:a", "aac",
            "-b:a", "320k",
            "-ar", "48000",
            "-shortest",
            str(output_path)
        ]
    else:
        # Pure pristine Full HD stillimage mode: exact reproduction of the thumbnail in 1080p
        cmd = [
            ffmpeg_exe,
            "-y",
            "-loop", "1",
            "-framerate", "30",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-preset", "slow",
            "-crf", "17",
            "-pix_fmt", "yuv420p",
            "-color_range", "1",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-c:a", "aac",
            "-b:a", "320k",
            "-ar", "48000",
            "-shortest",
            str(output_path)
        ]

    logger.info("Executing FFmpeg Full HD encoding...")
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        errors="replace"
    )

    if process.returncode != 0:
        logger.warning(f"FFmpeg primary encoding failed: {process.stderr[-400:]}. Retrying fallback...")
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
        fb_process = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, errors="replace")
        if fb_process.returncode != 0:
            logger.error(f"FFmpeg fallback failed: {fb_process.stderr}")
            raise RuntimeError(f"FFmpeg video encoding failed: {fb_process.stderr[-500:]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Video file was not created or has 0 bytes.")

    logger.info(f"Video created successfully: {output_path} ({output_path.stat().st_size / (1024*1024):.2f} MB)")
    return output_path
