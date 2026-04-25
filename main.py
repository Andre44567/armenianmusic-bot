import os
import tempfile
import re
import subprocess
import sys

import telebot
import yt_dlp

# ─────────────────────────────
# AUTO UPDATE yt-dlp
# ─────────────────────────────

def update_yt_dlp():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            check=True, capture_output=True
        )
    except:
        pass

update_yt_dlp()

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TOKEN չկա")

ADMIN_ID = 7304274135

START_PHOTO_URL = "https://i.imgur.com/qRNlg5M.png"

bot = telebot.TeleBot(TOKEN)
users = set()
playlists = {}

# ─────────────────────────────
# REGEX
# ─────────────────────────────

YOUTUBE_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+')
TIKTOK_REGEX = re.compile(r'(https?://)?(www\.|vm\.|vt\.)?tiktok\.com/\S+')
INSTAGRAM_REGEX = re.compile(r'(https?://)?(www\.)?instagram\.com/\S+')

# ─────────────────────────────
# START
# ─────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    users.add(message.from_user.id)

    bot.send_photo(
        message.chat.id,
        START_PHOTO_URL,
        caption=
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search-երգի անուն — Որոնել
        "🎧 /download-երգի անուն — Ներբեռնել
        "🎵 TikTok / Instagram / YouTube\n"
        "📋 /playlist-Պլեյլիստ տեսնել
        "📢 /broadcast (admin)"
    )

# ─────────────────────────────
# BROADCAST
# ─────────────────────────────

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    users.add(message.from_user.id)

    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Դու ադմին չես")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ /broadcast տեքստ")
        return

    text = parts[1]

    ok = 0
    fail = 0

    msg = bot.send_message(message.chat.id, "📤 ուղարկվում է...")

    for uid in list(users):
        try:
            bot.send_message(uid, f"📢 {text}")
            ok += 1
        except:
            fail += 1

    bot.edit_message_text(
        f"✅ ուղարկվեց {ok}\n❌ չստացվեց {fail}",
        message.chat.id,
        msg.message_id
    )

# ─────────────────────────────
# SEARCH
# ─────────────────────────────

@bot.message_handler(commands=['search'])
def search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ /search երգ")
        return

    query = parts[1]

    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)

    entry = info["entries"][0]

    bot.send_message(
        message.chat.id,
        f"🎵 {entry['title']}\n🔗 {entry['webpage_url']}"
    )

# ─────────────────────────────
# AUDIO DOWNLOAD
# ─────────────────────────────

def download_audio(q):
    tmp = tempfile.mkdtemp()

    try:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp}/%(title)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(q, download=True)

        for f in os.listdir(tmp):
            if f.endswith(".mp3") or f.endswith(".m4a"):
                return os.path.join(tmp, f), tmp, info.get("title")

        return None, tmp, None
    except:
        return None, tmp, None

# ─────────────────────────────
# MEDIA DOWNLOAD
# ─────────────────────────────

def download_media(url):
    tmp = tempfile.mkdtemp()

    try:
        opts = {
            "outtmpl": f"{tmp}/%(title)s.%(ext)s",
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title")

        video = None
        image = None

        for f in os.listdir(tmp):
            if f.endswith((".mp4", ".mov", ".webm")):
                video = os.path.join(tmp, f)
            if f.endswith((".jpg", ".png", ".jpeg")):
                image = os.path.join(tmp, f)

        return video, image, tmp, title
    except:
        return None, None, tmp, None

# ─────────────────────────────
def cleanup(tmp):
    try:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    except:
        pass

# ─────────────────────────────
def send_audio(chat, path, title):
    with open(path, "rb") as f:
        bot.send_audio(chat, f, title=title)

def send_video(chat, path, title):
    with open(path, "rb") as f:
        bot.send_video(chat, f, caption=title)

def send_photo(chat, path, title):
    with open(path, "rb") as f:
        bot.send_photo(chat, f, caption=title)

# ─────────────────────────────
# HANDLERS
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
def yt(message):
    url = YOUTUBE_REGEX.search(message.text).group(0)
    file, tmp, title = download_audio(url)

    if file:
        send_audio(message.chat.id, file, title)

    cleanup(tmp)

@bot.message_handler(func=lambda m: bool(TIKTOK_REGEX.search(m.text or "")))
def tt(message):
    url = TIKTOK_REGEX.search(message.text).group(0)
    video, image, tmp, title = download_media(url)

    if video:
        send_video(message.chat.id, video, title)
    elif image:
        send_photo(message.chat.id, image, title)

    cleanup(tmp)

@bot.message_handler(func=lambda m: bool(INSTAGRAM_REGEX.search(m.text or "")))
def ig(message):
    url = INSTAGRAM_REGEX.search(message.text).group(0)
    video, image, tmp, title = download_media(url)

    if video:
        send_video(message.chat.id, video, title)
    elif image:
        send_photo(message.chat.id, image, title)

    cleanup(tmp)

# ─────────────────────────────

print("BOT RUNNING...")
bot.polling(none_stop=True)
