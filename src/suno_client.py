import time
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import (
    SUNO_MODE,
    SUNO_COOKIE,
    SUNO_API_URL,
    SUNO_API_KEY,
    TEMP_DIR,
)

logger = logging.getLogger(__name__)


class SunoClient:
    """
    Client for composing music with Suno AI.
    Supports:
      1. Direct Suno session cookie with automatic Clerk JWT exchange (studio-api.suno.ai)
      2. Standard Suno API Gateway / Self-hosted endpoint
    """

    def __init__(self, cookie: Optional[str] = None, mode: Optional[str] = None):
        self.mode = mode or SUNO_MODE
        self.cookie = cookie or SUNO_COOKIE
        self.api_url = SUNO_API_URL
        self.api_key = SUNO_API_KEY
        self._cached_jwt: Optional[str] = None
        self._jwt_expires_at: float = 0

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Builds authorization headers for Suno Studio API.
        Automatically obtains or refreshes the Clerk JWT token if needed.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Origin": "https://suno.com",
            "Referer": "https://suno.com/",
            "Content-Type": "application/json"
        }

        # If user passed a JWT token directly
        if self.cookie.startswith("ey"):
            import base64
            import json
            try:
                parts = self.cookie.split(".")
                if len(parts) >= 2:
                    padding = "=" * (-len(parts[1]) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
                    exp = payload.get("exp")
                    if exp and time.time() > exp:
                        exp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))
                        logger.error(
                            f"\n[SUNO AUTH ERROR] The configured SUNO_COOKIE is a temporary JWT access token that EXPIRED on {exp_str}!\n"
                            "Suno access tokens (starting with 'ey') only last 1 hour.\n"
                            "👉 For 100% automated daily generation: Provide the persistent browser 'Cookie' header (starts with '__client' or '__session')\n"
                            "from suno.com so the bot can auto-refresh fresh tokens daily!\n"
                        )
            except Exception:
                pass
            headers["Authorization"] = f"Bearer {self.cookie}"
            return headers

        # If we have a cached JWT that hasn't expired (tokens usually valid for 60s)
        if self._cached_jwt and time.time() < self._jwt_expires_at:
            headers["Authorization"] = f"Bearer {self._cached_jwt}"
            return headers

        # Exchange browser cookie with Clerk for fresh JWT
        jwt = self._exchange_cookie_for_jwt()
        if jwt:
            self._cached_jwt = jwt
            self._jwt_expires_at = time.time() + 50  # Cache for 50s
            headers["Authorization"] = f"Bearer {jwt}"
        else:
            # Fallback: pass cookie directly
            headers["Cookie"] = self.cookie

        return headers

    def _exchange_cookie_for_jwt(self) -> Optional[str]:
        """
        Hits Clerk authentication endpoint using browser session cookies
        to retrieve a fresh JWT token for studio-api.suno.ai.
        """
        try:
            logger.info("Attempting automatic Clerk session refresh using browser cookie...")
            clerk_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Cookie": self.cookie,
                "Origin": "https://suno.com",
                "Referer": "https://suno.com/"
            }

            # 1. Fetch active session ID
            session_url = "https://clerk.suno.com/v1/client?_clerk_js_version=5.15.0"
            res = requests.get(session_url, headers=clerk_headers, timeout=15)
            if res.status_code != 200:
                logger.warning(f"Clerk client request returned status {res.status_code}: {res.text[:120]}")
                return None

            data = res.json()
            session_id = data.get("response", {}).get("last_active_session_id")
            if not session_id:
                sessions = data.get("response", {}).get("sessions", [])
                if sessions:
                    session_id = sessions[0].get("id")

            if not session_id:
                logger.warning("Could not find active session_id in Clerk response. Cookie may be invalid or expired.")
                return None

            # 2. Mint session token
            token_url = f"https://clerk.suno.com/v1/client/sessions/{session_id}/tokens?_clerk_js_version=5.15.0"
            token_res = requests.post(token_url, headers=clerk_headers, timeout=15)
            if token_res.status_code == 200:
                jwt = token_res.json().get("jwt")
                if jwt:
                    logger.info("Successfully refreshed fresh Suno Clerk JWT token for session.")
                    return jwt
            else:
                logger.warning(f"Clerk token minting returned status {token_res.status_code}: {token_res.text[:120]}")

        except Exception as e:
            logger.warning(f"Clerk token refresh exception: {e}")

        return None

    def get_user_info(self) -> Dict[str, Any]:
        """
        Verify connection and fetch billing/credits information from Suno.
        """
        if self.mode == "cookie":
            headers = self.get_auth_headers()
            url = "https://studio-api.prod.suno.com/api/billing/info/"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                # Also try feed endpoint to verify session
                resp = requests.get("https://studio-api.prod.suno.com/api/feed/", headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        elif self.mode == "api_gateway":
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(f"{self.api_url}/api/get_limit", headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def compose_song(self, title: str, style_tags: str, lyrics: str, output_path: Optional[Path] = None) -> Path:
        """
        Generate music using Suno AI and download the resulting MP3 audio file.
        """
        if output_path is None:
            output_path = TEMP_DIR / "generated_song.mp3"

        if self.mode == "cookie":
            return self._compose_via_cookie(title, style_tags, lyrics, output_path)
        elif self.mode == "api_gateway":
            return self._compose_via_api_gateway(title, style_tags, lyrics, output_path)
        else:
            raise ValueError(f"Unsupported SUNO_MODE: {self.mode}. Must be 'cookie' or 'api_gateway'.")

    def _compose_via_cookie(self, title: str, style_tags: str, lyrics: str, output_path: Path) -> Path:
        """
        Calls Suno's studio API using session cookie / JWT authentication.
        """
        logger.info("Submitting song generation request to Suno...")

        headers = self.get_auth_headers()

        payload = {
            "prompt": lyrics,
            "tags": style_tags,
            "title": title,
            "make_instrumental": False,
            "mv": "chirp-v3-5"
        }

        generate_endpoint = "https://studio-api.prod.suno.com/api/generate/v2/"

        response = requests.post(generate_endpoint, json=payload, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Suno generate request failed: {response.status_code} - {response.text}")
            response.raise_for_status()

        data = response.json()
        clips = data.get("clips", [])
        if not clips:
            raise RuntimeError(f"No clips returned from Suno API: {data}")

        clip_id = clips[0]["id"]
        logger.info(f"Suno generation initiated. Clip ID: {clip_id}. Polling for completion...")

        # Poll status until audio is ready
        audio_url = self._poll_suno_cookie_status(clip_id)
        return self._download_file(audio_url, output_path)

    def _poll_suno_cookie_status(self, clip_id: str, timeout_seconds: int = 360) -> str:
        """
        Polls the Suno feed endpoint until the clip is completed and provides an audio URL.
        """
        feed_endpoint = f"https://studio-api.prod.suno.com/api/feed/?ids={clip_id}"
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            time.sleep(10)
            try:
                headers = self.get_auth_headers()
                resp = requests.get(feed_endpoint, headers=headers, timeout=30)
                if resp.status_code == 200:
                    clips = resp.json()
                    for clip in clips:
                        if clip.get("id") == clip_id:
                            status = clip.get("status")
                            audio_url = clip.get("audio_url")
                            logger.info(f"Suno Clip [{clip_id}] status: {status}")

                            if status in ("complete", "streaming") and audio_url:
                                logger.info(f"Suno song generated successfully! URL: {audio_url}")
                                return audio_url
                            elif status == "error":
                                raise RuntimeError(f"Suno generation failed for clip {clip_id}: {clip.get('error_message')}")
            except Exception as e:
                logger.warning(f"Error while polling Suno status: {e}. Retrying...")

        raise TimeoutError(f"Suno generation timed out after {timeout_seconds} seconds.")

    def _compose_via_api_gateway(self, title: str, style_tags: str, lyrics: str, output_path: Path) -> Path:
        """
        Calls a standard Suno API gateway or self-hosted instance (e.g. suno-api / 3rd party provider).
        """
        logger.info(f"Submitting song generation request to Suno API Gateway ({self.api_url})...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": lyrics,
            "tags": style_tags,
            "title": title,
            "make_instrumental": False,
            "wait_audio": False
        }

        generate_endpoint = f"{self.api_url}/api/generate"
        response = requests.post(generate_endpoint, json=payload, headers=headers, timeout=60)

        if response.status_code not in (200, 201):
            logger.error(f"Suno API Gateway request failed: {response.status_code} - {response.text}")
            response.raise_for_status()

        data = response.json()
        task_id = None
        if isinstance(data, list) and len(data) > 0:
            task_id = data[0].get("id")
        elif isinstance(data, dict):
            task_id = data.get("id") or data.get("task_id") or data.get("data", {}).get("task_id")

        if not task_id:
            raise RuntimeError(f"Could not extract task/clip ID from API Gateway response: {data}")

        logger.info(f"Suno Gateway Task ID: {task_id}. Polling for completion...")

        # Poll status
        audio_url = self._poll_gateway_status(task_id, headers)
        return self._download_file(audio_url, output_path)

    def _poll_gateway_status(self, task_id: str, headers: dict, timeout_seconds: int = 360) -> str:
        """
        Polls the Suno API gateway endpoint until generation finishes.
        """
        poll_endpoint = f"{self.api_url}/api/get?ids={task_id}"
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            time.sleep(10)
            try:
                resp = requests.get(poll_endpoint, headers=headers, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    clips = result if isinstance(result, list) else result.get("data", [result])
                    for clip in clips:
                        status = clip.get("status")
                        audio_url = clip.get("audio_url")
                        logger.info(f"Task [{task_id}] status: {status}")

                        if status in ("complete", "SUCCESS", "streaming") and audio_url:
                            return audio_url
                        elif status in ("error", "FAILED"):
                            raise RuntimeError(f"Suno Gateway generation failed: {clip}")
            except Exception as e:
                logger.warning(f"Error checking gateway status: {e}. Retrying...")

        raise TimeoutError(f"Suno API gateway timed out after {timeout_seconds} seconds.")

    def _download_file(self, url: str, output_path: Path) -> Path:
        """
        Downloads the generated audio file from the remote URL to a local file.
        """
        logger.info(f"Downloading generated song from {url} to {output_path}...")
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"Audio file downloaded successfully. Size: {output_path.stat().st_size} bytes")
        return output_path
