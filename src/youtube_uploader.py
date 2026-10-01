import os
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from src.config import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
    YOUTUBE_PRIVACY_STATUS
)

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


class YouTubeUploader:
    """
    Automated YouTube Video & Thumbnail Uploader using YouTube Data API v3
    and OAuth 2.0 Refresh Token.
    """

    def __init__(self):
        self.client_id = YOUTUBE_CLIENT_ID
        self.client_secret = YOUTUBE_CLIENT_SECRET
        self.refresh_token = YOUTUBE_REFRESH_TOKEN
        self.privacy_status = YOUTUBE_PRIVACY_STATUS

    def get_authenticated_service(self):
        """
        Creates an authorized YouTube API service using the stored refresh token.
        Automatically handles token refreshing.
        """
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise ValueError(
                "YouTube credentials missing. Ensure YOUTUBE_CLIENT_ID, "
                "YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN are set."
            )

        credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=YOUTUBE_UPLOAD_SCOPE
        )

        # Refresh token to verify authorization
        credentials.refresh(Request())
        return build("youtube", "v3", credentials=credentials)

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        thumbnail_path: Optional[Path] = None,
        privacy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads a video to YouTube with metadata and custom thumbnail.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        privacy_status = privacy or self.privacy_status
        logger.info(f"Authenticating with YouTube API to upload: '{title}' (Privacy: {privacy_status})...")

        youtube = self.get_authenticated_service()

        body = {
            "snippet": {
                "title": title[:100],  # YouTube title limit is 100 characters
                "description": description[:5000],  # Description limit is 5000 characters
                "tags": tags or ["music", "original song", "ai music"],
                "categoryId": "10"  # Category 10 is 'Music'
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5  # 5MB chunks
        )

        insert_request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info("Uploading video stream...")
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        logger.info(f"Video upload completed! Video ID: {video_id}")
        logger.info(f"Watch URL: {video_url}")

        # Upload custom thumbnail if provided
        if thumbnail_path and thumbnail_path.exists():
            self._upload_thumbnail(youtube, video_id, thumbnail_path)

        return {
            "video_id": video_id,
            "url": video_url,
            "title": title,
            "privacy": privacy_status
        }

    def _upload_thumbnail(self, youtube, video_id: str, thumbnail_path: Path):
        """
        Sets a custom thumbnail for the specified video.
        """
        try:
            logger.info(f"Uploading custom thumbnail from {thumbnail_path} for video {video_id}...")
            mime = "image/png" if str(thumbnail_path).lower().endswith(".png") else "image/jpeg"
            thumb_media = MediaFileUpload(str(thumbnail_path), mimetype=mime)
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=thumb_media
            ).execute()
            logger.info("Custom thumbnail uploaded successfully.")
        except HttpError as e:
            logger.warning(
                f"Failed to set custom thumbnail: {e}. "
                "(Note: Channel must have phone verification enabled for custom thumbnails on YouTube)."
            )
        except Exception as e:
            logger.warning(f"Unexpected error uploading thumbnail: {e}")
