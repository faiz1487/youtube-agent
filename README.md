# 🎵 Daily Automated YouTube AI Music Channel Agent

An autonomous, fully scheduled AI agent that writes, composes, visualizes, and publishes original songs to your YouTube channel every day via **GitHub Actions**.

---

## 🌟 How It Works

```
                     ┌────────────────────────┐
                     │  GitHub Actions (Cron) │
                     │   Runs Daily / Manual  │
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │    OpenAI (ChatGPT)    │
                     │  • Selects Music Theme │
                     │  • Writes Song Lyrics  │
                     │  • Generates SEO Tags  │
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │        Suno AI         │
                     │ • Composes Vocal Track │
                     │ • Generates Master MP3 │
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │    DALL-E 3 + FFmpeg   │
                     │ • 16:9 Cover Art       │
                     │ • Audio Visualizer Wave│
                     │ • 1080p MP4 Render     │
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │  YouTube Data API v3   │
                     │ • Headless Upload      │
                     │ • Sets Custom Thumbnail│
                     │ • Titles, Tags, Lyrics │
                     └────────────────────────┘
```

---

## 📁 Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── daily_upload.yml       # Scheduled GitHub Actions daily workflow
├── src/
│   ├── __init__.py
│   ├── config.py                  # Credentials and environment configuration
│   ├── lyrics_generator.py        # ChatGPT lyrics & metadata prompt engine
│   ├── suno_client.py             # Suno AI music composer & downloader
│   ├── cover_generator.py         # DALL-E 3 / Pillow 16:9 cover visualizer
│   ├── video_maker.py             # FFmpeg 1080p video & waveform renderer
│   ├── youtube_uploader.py        # YouTube Data API v3 OAuth uploader
│   └── main.py                    # Master orchestrator script
├── scripts/
│   └── setup_youtube_oauth.py     # 1-time local script to get YouTube Refresh Token
├── .env.example                   # Environment variables template
├── requirements.txt               # Python package dependencies
├── .gitignore                     # Git exclusions
└── README.md                      # Setup and deployment documentation
```

---

## 🚀 Quick Setup Guide

### Step 1: Clone & Install Dependencies Locally
```bash
git clone <your-repo-url>
cd "youtube channel"
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

---

### Step 2: Get Your API Credentials

#### 1. OpenAI API Key (ChatGPT & DALL-E 3)
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Create and copy a new secret key (`sk-...`).

#### 2. Suno AI Credentials
You can use **either** your personal Suno account cookie or a Suno API gateway:
- **Option A (Personal Suno Account - Free / Subscription)**:
  1. Open [suno.com](https://suno.com) in your browser and log in.
  2. Press `F12` to open Developer Tools -> go to the **Network** tab.
  3. Create or play any song, look for any request to `studio-api.suno.ai`.
  4. In the request headers, copy the full `cookie` header value (or copy the `__client` session token).
  5. Set `SUNO_MODE=cookie` and paste into `SUNO_COOKIE`.
- **Option B (Suno API Gateway / Self-Hosted Provider)**:
  1. Set `SUNO_MODE=api_gateway`.
  2. Provide `SUNO_API_URL` and `SUNO_API_KEY`.

#### 3. YouTube Data API & OAuth Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `YouTube-Music-Bot`).
3. In the sidebar, go to **APIs & Services** -> **Library**.
4. Search for **YouTube Data API v3** and click **Enable**.
5. Go to **APIs & Services** -> **OAuth consent screen**:
   - User Type: **External**.
   - App name: `YouTube Music Bot`.
   - Add your email in User support email and Developer contact info.
   - Under **Scopes**, add `.../auth/youtube.upload` and `.../auth/youtube`.
   - Under **Test users**, add your own Google email address (the one connected to your YouTube channel).
6. Go to **APIs & Services** -> **Credentials**:
   - Click **Create Credentials** -> **OAuth client ID**.
   - Application type: **Desktop app**.
   - Name: `YouTube Bot Client`.
   - Copy your **Client ID** and **Client Secret**.

---

### Step 3: Run the YouTube Authorization Helper
Run this one-time command on your local machine:
```bash
python scripts/setup_youtube_oauth.py
```
- Paste your `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET`.
- Your browser will open asking you to select your YouTube channel and grant permission.
- The script will capture and display your permanent `YOUTUBE_REFRESH_TOKEN`!

---

### Step 4: Add GitHub Repository Secrets
Push your repository to GitHub, then navigate to:
**GitHub Repository** ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**.

Add the following secrets:

| Secret Name | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API Key (`sk-...`) |
| `SUNO_COOKIE` | Your Suno session cookie (if `SUNO_MODE=cookie`) |
| `YOUTUBE_CLIENT_ID` | Google OAuth Client ID |
| `YOUTUBE_CLIENT_SECRET` | Google OAuth Client Secret |
| `YOUTUBE_REFRESH_TOKEN` | OAuth Refresh Token obtained in Step 3 |

*(Optional Secrets)*:
- `SUNO_MODE`: `cookie` or `api_gateway` (default: `cookie`)
- `SUNO_API_URL`: Gateway URL if using an aggregator
- `SUNO_API_KEY`: Gateway Key if using an aggregator
- `YOUTUBE_PRIVACY_STATUS`: `public`, `unlisted`, or `private` (default: `public`)
- `MUSIC_GENRES`: Comma-separated genre list (e.g. `Synthwave,Lo-Fi Chillhop,Indie Pop`)

---

## ⚡ Running & Testing

### 1. Test Locally (Dry-Run Mode)
You can test the entire pipeline locally without spending API credits or uploading anything to YouTube:
```bash
python src/main.py --dry-run
```

### 2. Manual Trigger via GitHub Actions
1. Go to your repository on GitHub.
2. Click the **Actions** tab.
3. Select **Daily YouTube AI Music Agent** in the left sidebar.
4. Click **Run workflow**:
   - You can specify a custom genre (e.g. `Lo-Fi Chillhop`), theme, and privacy (`unlisted` or `public`).
   - Click **Run workflow**!

### 3. Automated Daily Schedule
The GitHub Actions workflow is scheduled with cron:
```yaml
schedule:
  - cron: '0 14 * * *'  # Runs daily at 14:00 UTC
```
To adjust the daily publishing time, simply edit `.github/workflows/daily_upload.yml`.

---

## 🎛️ Customization & Features

- **Audio Visualizer**: Uses FFmpeg's `showwaves` audio filter to render dynamic visualizer waves over the cover art at 1080p 30fps.
- **Fail-Safe Fallbacks**: If DALL-E 3 fails or hits rate limits, the agent automatically falls back to an aesthetic procedural gradient cover art generator with Pillow.
- **Viral SEO Descriptions**: ChatGPT automatically writes full song descriptions containing lyrics, timestamps, production credits, and hashtags to maximize search rank.
- **Custom Thumbnails**: The generated 16:9 cover art is automatically set as the custom thumbnail on YouTube.
