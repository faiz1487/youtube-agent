"""
One-Time YouTube OAuth Setup Script
====================================
Run this script ONCE on your local computer to authorize access to your YouTube channel.
It will generate the `YOUTUBE_REFRESH_TOKEN` needed for your GitHub Actions agent to
upload videos daily without asking for your password or manual authorization ever again.

Usage:
  python scripts/setup_youtube_oauth.py
"""

import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube upload and management scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


def main():
    print("=" * 65)
    print("      YOUTUBE OAUTH 2.0 ONE-TIME SETUP FOR GITHUB ACTIONS")
    print("=" * 65)
    print("\nBefore starting, ensure you have created an OAuth 2.0 Client ID")
    print("in Google Cloud Console (Application type: Desktop App).")
    print("Docs: https://console.cloud.google.com/apis/credentials\n")

    client_id = os.getenv("YOUTUBE_CLIENT_ID") or input("Enter your YOUTUBE_CLIENT_ID: ").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET") or input("Enter your YOUTUBE_CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        print("\n[ERROR] Both Client ID and Client Secret are required.")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/"]
        }
    }

    print("\n[1/3] Starting local authorization server...")
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=SCOPES
    )

    print("[2/3] Opening your browser for Google / YouTube authorization...")
    print("      Please sign in and click 'Continue' / 'Allow'...")

    # Run local server on fixed port to capture refresh_token
    credentials = flow.run_local_server(
        port=8080,
        prompt="consent",
        access_type="offline"
    )

    refresh_token = credentials.refresh_token

    if not refresh_token:
        print("\n[WARNING] No refresh token returned!")
        print("This usually happens if authorization was already granted previously.")
        print("To fix, revoke app access in your Google Account security settings and re-run.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("         SUCCESS! YOUR CREDENTIALS HAVE BEEN GENERATED")
    print("=" * 65)
    print("\nAdd these three values to your GitHub Repository Secrets:")
    print("(GitHub Repo -> Settings -> Secrets and variables -> Actions -> New repository secret)\n")
    print(f"YOUTUBE_CLIENT_ID={client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={refresh_token}")
    print("\n" + "=" * 65)

    # Optional: offer to save to .env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    save = input(f"\nDo you want to save these to your local .env file? (y/n): ").strip().lower()
    if save in ("y", "yes"):
        lines = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()

        # Update or append
        keys_to_set = {
            "YOUTUBE_CLIENT_ID": client_id,
            "YOUTUBE_CLIENT_SECRET": client_secret,
            "YOUTUBE_REFRESH_TOKEN": refresh_token
        }

        updated_lines = []
        existing_keys = set()
        for line in lines:
            key_found = False
            for k, v in keys_to_set.items():
                if line.startswith(f"{k}="):
                    updated_lines.append(f"{k}={v}")
                    existing_keys.add(k)
                    key_found = True
                    break
            if not key_found:
                updated_lines.append(line)

        for k, v in keys_to_set.items():
            if k not in existing_keys:
                updated_lines.append(f"{k}={v}")

        env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        print(f"Successfully saved to {env_path}")


if __name__ == "__main__":
    main()
