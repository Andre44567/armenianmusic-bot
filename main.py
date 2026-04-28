import os
import tempfile
import re
import subprocess
import sys

import telebot
import yt_dlp

# ─────────────────────────────
# INSTALL DEPS
# ─────────────────────────────

def install_deps():
    for pkg in ["yt-dlp", "gallery-dl", "spotdl"]:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", pkg,
                 "--break-system-packages"],
                capture_output=True
            )
            print(f"✅ {pkg} OK")
        except Exception as e:
            print(f"⚠️ {pkg}: {e}")

install_deps()

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չկա")

ADMIN_ID = 7304274135

bot = telebot.TeleBot(TOKEN)
playlists = {}
users = set()

WELCOME_IMAGE_URL = "https://i.ibb.co/wFSQWyb8/IMG-20260427-194624-991.jpg"

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)
TIKTOK_REGEX = re.compile(
    r'(https?://)?(www\.|vm\.|vt\.)?(tiktok\.com/)[\S]+'
)
INSTAGRAM_REGEX = re.compile(
    r'(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+'
)
PINTEREST_REGEX = re.compile(
    r'(https?://)?(www\.|[a-z]{2}\.)?pinterest\.(com|co\.[a-z]+)/pin/[\w\-]+'
    r'|(https?://)?pin\.it/[\w]+'
)

def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = has_ffmpeg()
print(f"ffmpeg: {'✅' if FFMPEG_AVAILABLE else '❌'}")

# ─── YouTube Cookies ───
COOKIES_FILE = "/tmp/youtube_cookies.txt"
YT_COOKIES = os.environ.get("YOUTUBE_COOKIES", "")
if YT_COOKIES:
    with open(COOKIES_FILE, "w") as f:
        f.write(YT_COOKIES)
    print("✅ YouTube cookies loaded")
else:
    COOKIES_FILE = None
    print("⚠️ No YouTube cookies")

# ─────────────────────────────
# START / HELP
# ─────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    users.add(message.from_user.id)
    text = (
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն — Որոնել\n"
        "🎧 /download երգի անուն — Ներբեռնել\n"
        "🔗 YouTube հղում — Ուղղակի ներբեռնել\n"
        "🎵 TikTok հղում — Վիդեո ներբեռնել\n"
        "📸 Instagram հղում — Վիդեո/նկար ներբեռնել\n"
        "📌 Pinterest հղում — Նկար/վիդեո ներբեռնել\n"
        "➕ /add երգի անուն — Պլեյլիստ ավելացնել\n"
        "📋 /playlist — Պլեյլիստ տեսնել\n"
        "🗑 /remove համար — Հեռացնել\n"
        "🔄 /update — Թարմացնել"
    )
    try:
        bot.send_photo(message.chat.id, photo=WELCOME_IMAGE_URL, caption=text)
    except Exception:
        bot.send_message(message.chat.id, text)

# ─────────────────────────────
# UPDATE
# ─────────────────────────────

@bot.message_handler(commands=['update'])
def update_command(message):
    users.add(message.from_user.id)
    msg = bot.send_message(message.chat.id, "🔄 Թարմացնում եմ...")
    install_deps()
    global FFMPEG_AVAILABLE
    FFMPEG_AVAILABLE = has_ffmpeg()
    bot.edit_message_text("✅ Թարմացվեց", message.chat.id, msg.message_id)

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
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /broadcast Քո նամակը")
        return
    text = parts[1]
    success = 0
    failed = 0
    msg = bot.send_message(message.chat.id, f"📤 Ուղարկում եմ {len(users)} հոգու...")
    for uid in users.copy():
        try:
            bot.send_message(uid, f"📢 {text}")
            success += 1
        except Exception:
            failed += 1
    bot.edit_message_text(
        f"✅ Ուղարկվեց {success} հոգու\n❌ Չստացվեց {failed} հոգու",
        message.chat.id, msg.message_id
    )

# ─────────────────────────────
# SEARCH
# ─────────────────────────────

@bot.message_handler(commands=['search'])
def search(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /search երգի անուն")
        return
    query = parts[1]
    bot.send_message(message.chat.id, "🔍 Որոնում եմ...")
    for source in [f"scsearch1:{query}", f"ytsearch1:{query}"]:
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(source, download=False)
            if not info or "entries" not in info or not info["entries"]:
                continue
            entry = info["entries"][0]
            title = entry.get("title", "Անհայտ")
            url = entry.get("webpage_url") or entry.get("url", "")
            duration = entry.get("duration", 0) or 0
            mins, secs = divmod(int(duration), 60)
            bot.send_message(message.chat.id, f"🎵 {title}\n⏱ {mins}:{secs:02d}\n🔗 {url}")
            return
        except Exception as e:
            print(f"SEARCH ERROR: {e}")
            continue
    bot.send_message(message.chat.id, "❌ Չգտնվեց")

# ─────────────────────────────
# AUDIO DOWNLOAD
# spotdl → SoundCloud → YouTube
# ─────────────────────────────

def download_audio(query_or_url):
    tmp_dir = tempfile.mkdtemp()
    title = "Անհայտ"
    is_url = bool(YOUTUBE_REGEX.match(query_or_url.strip()))

    # 1. spotdl
    try:
        result = subprocess.run(
            ["spotdl", "download", query_or_url,
             "--output", tmp_dir,
             "--format", "mp3",
             "--bitrate", "128k"],
            capture_output=True, text=True, timeout=120
        )
        print("spotdl:", result.stdout[-300:])
        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".ogg", ".opus")):
                title = f.rsplit(".", 1)[0]
                print(f"✅ spotdl: {title}")
                return os.path.join(tmp_dir, f), tmp_dir, title
    except Exception as e:
        print(f"spotdl failed: {e}")

    # 2. SoundCloud
    try:
        sc_query = f"scsearch1:{query_or_url}" if not is_url else f"scsearch1:{query_or_url}"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "socket_timeout": 30,
        }
        if FFMPEG_AVAILABLE:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(sc_query, download=True)
            if info and "entries" in info and info["entries"]:
                title = info["entries"][0].get("title", "Անհայտ")
            elif info:
                title = info.get("title", "Անհայտ")
        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".webm", ".ogg", ".opus")):
                print(f"✅ SoundCloud: {title}")
                return os.path.join(tmp_dir, f), tmp_dir, title
    except Exception as e:
        print(f"SoundCloud failed: {e}")

    # 3. Yandex Music
    try:
        ym_query = f"ymsearch:{query_or_url}" if not is_url else query_or_url
        ydl_opts_ym = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "socket_timeout": 30,
        }
        if FFMPEG_AVAILABLE:
            ydl_opts_ym["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }]
        with yt_dlp.YoutubeDL(ydl_opts_ym) as ydl:
            info = ydl.extract_info(ym_query, download=True)
            if info and "entries" in info and info["entries"]:
                title = info["entries"][0].get("title", "Անհայտ")
            elif info:
                title = info.get("title", "Անհայտ")
        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".webm", ".ogg", ".opus")):
                print(f"✅ Yandex Music: {title}")
                return os.path.join(tmp_dir, f), tmp_dir, title
    except Exception as e:
        print(f"Yandex Music failed: {e}")

    # 4. YouTube
    try:
        yt_source = query_or_url.strip() if is_url else f"ytsearch1:{query_or_url}"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "extractor_args": {"youtube": {"player_client": ["ios", "android"]}},
            "socket_timeout": 30,
        }
        if FFMPEG_AVAILABLE:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }]
        if COOKIES_FILE:
            ydl_opts["cookiefile"] = COOKIES_FILE
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(yt_source, download=True)
            if info and "entries" in info and info["entries"]:
                title = info["entries"][0].get("title", "Անհայտ")
            elif info:
                title = info.get("title", "Անհայտ")
        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".webm", ".ogg", ".opus")):
                print(f"✅ YouTube: {title}")
                return os.path.join(tmp_dir, f), tmp_dir, title
    except Exception as e:
        print(f"YouTube failed: {e}")

    return None, tmp_dir, None

# ─────────────────────────────
# MEDIA DOWNLOAD
# gallery-dl → yt-dlp
# ─────────────────────────────

def download_media(url):
    tmp_dir = tempfile.mkdtemp()
    title = "Անհայտ"

    # 1. gallery-dl
    try:
        result = subprocess.run(
            [sys.executable, "-m", "gallery_dl", url, "-D", tmp_dir],
            capture_output=True, text=True, timeout=60
        )
        print("gallery-dl:", result.stdout[-200:], result.stderr[-100:])
        files = sorted(os.listdir(tmp_dir))
        if files:
            f = files[0]
            title = f.rsplit(".", 1)[0]
            print(f"✅ gallery-dl: {f}")
            return os.path.join(tmp_dir, f), tmp_dir, title
    except Exception as e:
        print(f"gallery-dl failed: {e}")

    # 2. yt-dlp fallback
    try:
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "socket_timeout": 30,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = info.get("title", "Անհայտ")
        files = os.listdir(tmp_dir)
        if files:
            print(f"✅ yt-dlp media: {files[0]}")
            return os.path.join(tmp_dir, files[0]), tmp_dir, title
    except Exception as e:
        print(f"yt-dlp media failed: {e}")

    return None, tmp_dir, None

# ─────────────────────────────
# HELPERS
# ─────────────────────────────

def cleanup(tmp_dir):
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass

def send_audio_file(chat_id, file_path, title, msg_id):
    try:
        with open(file_path, "rb") as audio:
            bot.send_audio(chat_id, audio, title=title, performer="🎵")
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    except Exception as e:
        print(f"send_audio error: {e}")

def send_media_file(chat_id, file_path, title, msg_id, platform=""):
    try:
        ext = file_path.lower().rsplit(".", 1)[-1]
        if ext in ("jpg", "jpeg", "png", "webp"):
            with open(file_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"{platform} {title}")
        else:
            with open(file_path, "rb") as f:
                bot.send_video(chat_id, f, caption=f"{platform} {title}")
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    except Exception as e:
        print(f"send_media error: {e}")

# ─────────────────────────────
# HANDLERS
# ─────────────────────────────

@bot.message_handler(commands=['download'])
def download(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգի անուն")
        return
    query = parts[1]
    msg = bot.send_message(message.chat.id, "⏳ Ներբեռնում եմ...")
    file_path, tmp_dir, title = download_audio(query)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_audio_file(message.chat.id, file_path, title, msg.message_id)
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    cleanup(tmp_dir)


@bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
def handle_youtube(message):
    users.add(message.from_user.id)
    url = YOUTUBE_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "🔗 YouTube, ներբեռնում եմ...")
    file_path, tmp_dir, title = download_audio(url)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_audio_file(message.chat.id, file_path, title, msg.message_id)
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    cleanup(tmp_dir)


@bot.message_handler(func=lambda m: bool(TIKTOK_REGEX.search(m.text or "")))
def handle_tiktok(message):
    users.add(message.from_user.id)
    url = TIKTOK_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "🎵 TikTok, ներբեռնում եմ...")
    file_path, tmp_dir, title = download_media(url)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_media_file(message.chat.id, file_path, title, msg.message_id, "🎵")
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    cleanup(tmp_dir)


@bot.message_handler(func=lambda m: bool(INSTAGRAM_REGEX.search(m.text or "")))
def handle_instagram(message):
    users.add(message.from_user.id)
    url = INSTAGRAM_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "📸 Instagram, ներբեռնում եմ...")
    file_path, tmp_dir, title = download_media(url)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_media_file(message.chat.id, file_path, title, msg.message_id, "📸")
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    cleanup(tmp_dir)


@bot.message_handler(func=lambda m: bool(PINTEREST_REGEX.search(m.text or "")))
def handle_pinterest(message):
    users.add(message.from_user.id)
    url = PINTEREST_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "📌 Pinterest, ներբեռնում եմ...")
    file_path, tmp_dir, title = download_media(url)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_media_file(message.chat.id, file_path, title, msg.message_id, "📌")
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    cleanup(tmp_dir)

# ─────────────────────────────
# PLAYLIST
# ─────────────────────────────

@bot.message_handler(commands=['add'])
def add(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /add երգ")
        return
    playlists.setdefault(message.from_user.id, []).append(parts[1])
    bot.send_message(message.chat.id, "✅ Ավելացվեց")


@bot.message_handler(commands=['playlist'])
def playlist(message):
    users.add(message.from_user.id)
    uid = message.from_user.id
    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Դատարկ է")
        return
    text = "📋 Քո պլեյլիստը՝\n\n"
    for i, s in enumerate(playlists[uid], 1):
        text += f"{i}. 🎵 {s}\n"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['remove'])
def remove(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    uid = message.from_user.id
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /remove համար")
        return
    idx = int(parts[1]) - 1
    if uid in playlists and 0 <= idx < len(playlists[uid]):
        playlists[uid].pop(idx)
        bot.send_message(message.chat.id, "🗑 Ջնջվեց")
    else:
        bot.send_message(message.chat.id, "❌ Սխալ համար")

# ─────────────────────────────
# FALLBACK
# ─────────────────────────────

@bot.message_handler(func=lambda m: True)
def unknown(message):
    users.add(message.from_user.id)
    bot.send_message(message.chat.id, "❓ Գրիր /help")

# ─────────────────────────────
print("✅ BOT RUNNING...")
bot.polling(none_stop=True)
