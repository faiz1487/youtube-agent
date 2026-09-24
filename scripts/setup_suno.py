"""
Suno.com Connection & Verification Helper
=========================================
Run this script to test and connect your Suno account to the agent.
It validates your session cookie, fetches your credit balance, and saves
it to your local .env file.

Usage:
  python scripts/setup_suno.py
"""

import os
import sys
from pathlib import Path

# Ensure root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.suno_client import SunoClient


def print_instructions():
    print("=" * 70)
    print("           SUNO.COM ACCOUNT CONNECTION HELPER")
    print("=" * 70)
    print("\nHow to get your Suno Cookie in 30 seconds:")
    print(" 1. Open https://suno.com in Chrome/Edge/Brave and log in.")
    print(" 2. Press F12 (or Right-Click -> Inspect) and click the 'Network' tab.")
    print(" 3. In the filter box at the top, type: client?_clerk")
    print("    (If nothing shows up, refresh the page with F5).")
    print(" 4. Click on the request named 'client?_clerk_js_version=...'")
    print(" 5. In the 'Headers' tab on the right, scroll to 'Request Headers'.")
    print(" 6. Find 'Cookie:', right-click the text next to it, and click 'Copy value'.")
    print("=" * 70 + "\n")


def save_to_env(cookie: str):
    env_path = ROOT_DIR / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    keys_to_set = {
        "SUNO_MODE": "cookie",
        "SUNO_COOKIE": cookie
    }

    updated_lines = []
    existing_keys = set()
    for line in lines:
        matched = False
        for k, v in keys_to_set.items():
            if line.startswith(f"{k}="):
                updated_lines.append(f"{k}={v}")
                existing_keys.add(k)
                matched = True
                break
        if not matched:
            updated_lines.append(line)

    for k, v in keys_to_set.items():
        if k not in existing_keys:
            updated_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print(f"\n[OK] Successfully saved SUNO_COOKIE to {env_path}")


def main():
    print_instructions()

    cookie = input("Paste your Suno Cookie here: ").strip()

    # Clean quotes if user pasted with quotes
    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1]

    if not cookie:
        print("[ERROR] Cookie cannot be empty.")
        sys.exit(1)

    print("\n[1/2] Connecting to Suno and validating session...")
    client = SunoClient(cookie=cookie, mode="cookie")

    try:
        info = client.get_user_info()
        print("\n" + "=" * 70)
        print("          SUCCESS! SUNO ACCOUNT CONNECTED!")
        print("=" * 70)

        # Display user / credit info
        credits_left = info.get("total_credits_left") or info.get("credits_left") or info.get("monthly_usage")
        plan = info.get("monthly_limit") or info.get("tier") or "Active"

        if credits_left is not None:
            print(f" Remaining Credits: {credits_left}")
        if plan:
            print(f" Subscription Tier: {plan}")

        print("=" * 70)

        save_to_env(cookie)

        print("\nNext step for GitHub Actions:")
        print("Add this secret in your GitHub repository:")
        print("GitHub Repo -> Settings -> Secrets and variables -> Actions -> New secret")
        print("Name:  SUNO_COOKIE")
        print("Value: (The cookie you just pasted)")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n[WARNING] Could not verify account details automatically: {e}")
        print("However, your cookie format might still work for generating music.")
        save_choice = input("Do you still want to save this cookie to .env? (y/n): ").strip().lower()
        if save_choice in ("y", "yes"):
            save_to_env(cookie)


if __name__ == "__main__":
    main()
