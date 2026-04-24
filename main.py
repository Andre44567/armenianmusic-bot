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
        print("🔄 Թարմացնում եմ yt-dlp...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            check=True, capture_output=True
        )
        print("✅ yt-dlp թարմացվեց")
    except Exception as e:
        print(f"⚠️ yt-dlp թարմացումը ձախողվեց: {e}")

update_yt_dlp()


# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չկա")

bot = telebot.TeleBot(TOKEN)
playlists = {}

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)


# ─────────────────────────────
# START / HELP
# ─────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն — Որոնել և ստանալ հղում\n"
        "🎧 /download երգի անուն — Ներբեռնել MP3 ֆայլ\n"
        "🔗 YouTube հղում ուղարկիր — Ուղղակի ներբեռնել\n"
        "➕ /add երգի անուն — Ավելացնել պլեյլիստ\n"
        "📋 /playlist — Տեսնել պլեյլիստը\n"
        "🗑 /remove համար — Հեռացնել պլեյլիստից\n"
        "🔄 /update — Թարմացնել yt-dlp"
    )


# ─────────────────────────────
# UPDATE COMMAND
# ─────────────────────────────

@bot.message_handler(commands=['update'])
def update_command(message):
    msg = bot.send_message(message.chat.id, "🔄 Թարմացնում եմ yt-dlp...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            check=True, capture_output=True, text=True
        )
        version = yt_dlp.version.__version__
        bot.edit_message_text(
            f"✅ yt-dlp թարմացվեց\n📦 Տարբերակ: {version}",
            message.chat.id, msg.message_id
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Թարմացումը ձախողվեց\n{e}",
            message.chat.id, msg.message_id
        )


# ─────────────────────────────
# SEARCH — Ուղղված
# ─────────────────────────────

@bot.message_handler(commands=['search'])
def search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /search երգի անուն")
        return

    query = parts[1]
    bot.send_message(message.chat.id, "🔍 Որոնում եմ...")

    try:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "extract_flat": False,
            # Cookie-ի խնդիրը շրջանցելու համար
            "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)

        if not info or "entries" not in info or not info["entries"]:
            bot.send_message(message.chat.id, "❌ Չգտնվեց")
            return

        entry = info["entries"][0]
        title = entry.get("title", "Անհայտ")
        url = entry.get("webpage_url") or entry.get("url", "")
        duration = entry.get("duration", 0) or 0
        mins, secs = divmod(int(duration), 60)

        bot.send_message(
            message.chat.id,
            f"🎵 {title}\n"
            f"⏱ {mins}:{secs:02d}\n"
            f"🔗 {url}"
        )

    except Exception as e:
        print("SEARCH ERROR:", e)
        bot.send_message(message.chat.id, f"❌ Չգտնվեց\n⚠️ {str(e)[:100]}")


# ─────────────────────────────
# DOWNLOAD CORE — Ուղղված
# ─────────────────────────────

def download_audio(query_or_url):
    tmp_dir = tempfile.mkdtemp()
    is_url = bool(YOUTUBE_REGEX.match(query_or_url.strip()))
    source = query_or_url.strip() if is_url else f"ytsearch1:{query_or_url}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": False,  # Debug համար True-ից False
        # ffmpeg չկա — ուղղակի audio ներբեռնել առանց convert
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
    }

    title = "Անհայտ"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source, download=True)
            if info:
                if "entries" in info and info["entries"]:
                    title = info["entries"][0].get("title", "Անհայտ")
                else:
                    title = info.get("title", "Անհայտ")

        # MP3 կամ ցանկացած audio ֆայլ
        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".webm", ".ogg", ".opus")):
                return os.path.join(tmp_dir, f), tmp_dir, title

        return None, tmp_dir, None

    except Exception as e:
        print("DOWNLOAD ERROR:", e)
        return None, tmp_dir, None


# ffmpeg չկա — առանց postprocessor փորձ
def download_audio_no_ffmpeg(query_or_url):
    tmp_dir = tempfile.mkdtemp()
    is_url = bool(YOUTUBE_REGEX.match(query_or_url.strip()))
    source = query_or_url.strip() if is_url else f"ytsearch1:{query_or_url}"

    ydl_opts = {
        # m4a/webm/opus — ffmpeg-ից առանց
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
        "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": False,
        "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
    }

    title = "Անհայտ"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source, download=True)
            if info:
                if "entries" in info and info["entries"]:
                    title = info["entries"][0].get("title", "Անհայտ")
                else:
                    title = info.get("title", "Անհայտ")

        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".webm", ".ogg", ".opus")):
                return os.path.join(tmp_dir, f), tmp_dir, title

        return None, tmp_dir, None

    except Exception as e:
        print("DOWNLOAD NO-FFMPEG ERROR:", e)
        return None, tmp_dir, None


def cleanup(tmp_dir):
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass


# ─────────────────────────────
# DOWNLOAD COMMAND
# ─────────────────────────────

@bot.message_handler(commands=['download'])
def download(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգի անուն")
        return

    query = parts[1]
    msg = bot.send_message(message.chat.id, "⏳ Ներբեռնում եմ...")

    # Առաջին փորձ — ffmpeg-ով
    file_path, tmp_dir, title = download_audio(query)

    # Եթե ձախողվեց — առանց ffmpeg
    if not file_path or not os.path.exists(file_path):
        cleanup(tmp_dir)
        bot.edit_message_text("⚠️ Փորձում եմ այլ եղանակով...", message.chat.id, msg.message_id)
        file_path, tmp_dir, title = download_audio_no_ffmpeg(query)

    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        with open(file_path, "rb") as audio:
            bot.send_audio(message.chat.id, audio, title=title, performer="YouTube")
        bot.delete_message(message.chat.id, msg.message_id)
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n"
            "💡 Փորձիր /update հրամանը, հետո նորից",
            message.chat.id, msg.message_id
        )

    cleanup(tmp_dir)


# ─────────────────────────────
# YOUTUBE URL — ՈՒՂՂԱԿԻ
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
def handle_youtube_url(message):
    match = YOUTUBE_REGEX.search(message.text)
    url = match.group(0)

    msg = bot.send_message(message.chat.id, "🔗 YouTube հղում հայտնաբերվեց, ներբեռնում եմ...")

    file_path, tmp_dir, title = download_audio(url)

    if not file_path or not os.path.exists(file_path):
        cleanup(tmp_dir)
        bot.edit_message_text("⚠️ Փորձում եմ այլ եղանակով...", message.chat.id, msg.message_id)
        file_path, tmp_dir, title = download_audio_no_ffmpeg(url)

    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        with open(file_path, "rb") as audio:
            bot.send_audio(message.chat.id, audio, title=title, performer="YouTube")
        bot.delete_message(message.chat.id, msg.message_id)
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n"
            "💡 Փորձիր /update հրամանը, հետո նորից",
            message.chat.id, msg.message_id
        )
