import os
import tempfile
import re
import subprocess
import sys
import shutil
import requests
import telebot
import yt_dlp

# ─────────────────────────────
# AUTO-UPDATE yt-dlp
# ─────────────────────────────
def update_yt_dlp():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            check=True, capture_output=True
        )
        print("✅ yt-dlp թարմացվեց")
    except Exception as e:
        print(f"⚠️ yt-dlp թարմացման սխալ: {e}")

update_yt_dlp()

# ─────────────────────────────
# CONFIG & TOKENS
# ─────────────────────────────
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN-ը գտնված չէ Environment Variables-ում")

ADMIN_ID = 7304274135
RAPIDAPI_KEY = "84c6910a82mshb9fff0a8c0c62f1p109a93jsn9ce6c2818c4c"
RAPIDAPI_HOST = "social-download-all-in-one.p.rapidapi.com"
RAPIDAPI_URL = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"

RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/json",
}

# Յութուբի քուքիների ֆայլը (եթե կա)
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

bot = telebot.TeleBot(TOKEN)
playlists = {}
users = set()

# ─────────────────────────────
# REGEXES (Թարմացված)
# ─────────────────────────────
YOUTUBE_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|shorts/)?[\w\-]+')
TIKTOK_REGEX = re.compile(r'(https?://)?(www\.|vm\.|vt\.)?tiktok\.com/[\S]+')
INSTAGRAM_REGEX = re.compile(r'(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+')
# Pinterest-ի համար ավելացվել է pin.it տարբերակը
PINTEREST_REGEX = re.compile(r'(https?://)?(www\.|[a-z]{2}\.)?pinterest\.(com|co\.[a-z]+)/pin/[\w\-]+|https?://pin\.it/[\w\-]+')

# ─────────────────────────────
# UTILS
# ─────────────────────────────
def get_cookies_opts():
    if os.path.exists(COOKIES_FILE):
        return {"cookiefile": COOKIES_FILE}
    return {}

def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = has_ffmpeg()

def cleanup(tmp_dir):
    shutil.rmtree(tmp_dir, ignore_errors=True)

# ─────────────────────────────
# RAPIDAPI — SOCIAL DOWNLOADER
# ─────────────────────────────
def rapidapi_download(url):
    tmp_dir = tempfile.mkdtemp()
    try:
        resp = requests.post(
            RAPIDAPI_URL,
            headers=RAPIDAPI_HEADERS,
            json={"url": url},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"❌ RapidAPI սխալ ստատուս: {resp.status_code}")
            return None, tmp_dir, None
            
        data = resp.json()
        print("RAPIDAPI RESPONSE:", data)

        title = data.get("title") or data.get("desc") or "Media"
        medias = data.get("medias") or []

        if not medias:
            return None, tmp_dir, None

        # Ընտրում ենք լավագույն հղումը
        chosen = None
        for q in ["hd", "sd", "audio", "thumbnail"]:
            for m in medias:
                if m.get("quality") == q and m.get("url"):
                    chosen = m
                    break
            if chosen: break
        
        if not chosen: chosen = medias[0]
        
        media_url = chosen["url"]
        ext = chosen.get("extension") or "mp4"
        
        file_resp = requests.get(media_url, timeout=60, stream=True)
        file_resp.raise_for_status()

        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
        file_path = os.path.join(tmp_dir, f"{safe_title}.{ext}")

        with open(file_path, "wb") as f:
            for chunk in file_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return file_path, tmp_dir, title
    except Exception as e:
        print(f"⚠️ RapidAPI սխալ: {e}")
        return None, tmp_dir, None

# ─────────────────────────────
# YT-DLP CORE DOWNLOADERS
# ─────────────────────────────
def download_audio(query_or_url):
    tmp_dir = tempfile.mkdtemp()
    is_url = bool(YOUTUBE_REGEX.match(query_or_url.strip()))
    source
