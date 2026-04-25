import os
import tempfile
import re
import subprocess
import sys

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
        print(f"⚠️ {e}")

update_yt_dlp()

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չկա")

ADMIN_ID = 7304274135

# 👉 ԱՅՍՏԵՂ ԴՆՈՒՄ ԵՍ ՔՈ ՆԿԱՐԻ URL-ը
START_PHOTO_URL = "https://i.imgur.com/qRNlg5M.png"

bot = telebot.TeleBot(TOKEN)
playlists = {}
users = set()

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)

TIKTOK_REGEX = re.compile(
    r'(https?://)?(www\.|vm\.|vt\.)?(tiktok\.com/)[\S]+'
)

INSTAGRAM_REGEX = re.compile(
    r'(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+'
)

# ─────────────────────────────
def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = has_ffmpeg()

# ─────────────────────────────
# START
# ─────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    users.add(message.from_user.id)

    caption = (
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն\n"
        "🎧 /download երգի անուն\n"
        "🔗 YouTube link\n"
        "🎵 TikTok link\n"
        "📸 Instagram link\n"
    )

    bot.send_photo(message.chat.id, START_PHOTO_URL, caption=caption)

# ─────────────────────────────
# DOWNLOAD AUDIO (YouTube)
# ─────────────────────────────

def download_audio(query_or_url):
    tmp_dir = tempfile.mkdtemp()
    source = query_or_url.strip()

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source, download=True)
            title = info.get("title", "Unknown")

        for f in os.listdir(tmp_dir):
            if f.endswith(".mp3"):
                return os.path.join(tmp_dir, f), tmp_dir, title

        return None, tmp_dir, None

    except Exception as e:
        print(e)
        return None, tmp_dir, None

# ─────────────────────────────
# DOWNLOAD MEDIA (VIDEO + PHOTO)
# ─────────────────────────────

def download_media(url):
    tmp_dir = tempfile.mkdtemp()
    title = "Unknown"

    try:
        ydl_opts = {
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Unknown")

        video_file = None
        image_file = None

        for f in os.listdir(tmp_dir):
            path = os.path.join(tmp_dir, f)

            if f.endswith((".mp4", ".mov", ".webm", ".mkv")):
                video_file = path
            elif f.endswith((".jpg", ".jpeg", ".png")):
                image_file = path

        return video_file, image_file, tmp_dir, title

    except Exception as e:
        print(e)
        return None, None, tmp_dir, None

# ─────────────────────────────
def cleanup(tmp_dir):
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass

# ─────────────────────────────
# SEND FUNCTIONS
# ─────────────────────────────

def send_audio(chat_id, path, title):
    with open(path, "rb") as f:
        bot.send_audio(chat_id, f, title=title)

def send_video(chat_id, path, title):
    with open(path, "rb") as f:
        bot.send_video(chat_id, f, caption=title)

def send_photo(chat_id, path, title):
    with open(path, "rb") as f:
        bot.send_photo(chat_id, f, caption=title)

# ─────────────────────────────
# YOUTUBE
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
def youtube(message):
    url = YOUTUBE_REGEX.search(message.text).group(0)

    msg = bot.send_message(message.chat.id, "⏳ downloading...")

    file, tmp, title = download_audio(url)

    if file:
        send_audio(message.chat.id, file, title)
    else:
        bot.send_message(message.chat.id, "❌ error")

    cleanup(tmp)

# ─────────────────────────────
# TIKTOK
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(TIKTOK_REGEX.search(m.text or "")))
def tiktok(message):
    url = TIKTOK_REGEX.search(message.text).group(0)

    msg = bot.send_message(message.chat.id, "⏳ TikTok...")

    video, image, tmp, title = download_media(url)

    if video:
        send_video(message.chat.id, video, "🎵 TikTok " + title)
    elif image:
        send_photo(message.chat.id, image, "🎵 TikTok " + title)
    else:
        bot.send_message(message.chat.id, "❌ error")

    cleanup(tmp)

# ─────────────────────────────
# INSTAGRAM
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(INSTAGRAM_REGEX.search(m.text or "")))
def instagram(message):
    url = INSTAGRAM_REGEX.search(message.text).group(0)

    msg = bot.send_message(message.chat.id, "⏳ Instagram...")

    video, image, tmp, title = download_media(url)

    if video:
        send_video(message.chat.id, video, "📸 Instagram " + title)
    elif image:
        send_photo(message.chat.chat.id, image, "📸 Instagram " + title)
    else:
        bot.send_message(message.chat.id, "❌ error")

    cleanup(tmp)

# ─────────────────────────────
print("✅ BOT RUNNING...")
bot.polling(none_stop=True)
