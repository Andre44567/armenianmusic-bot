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
        print(f"⚠️ {e}")

update_yt_dlp()

# ─────────────────────────────
# COOKIES FILE — YouTube
# ─────────────────────────────

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

def get_cookies_opts():
    if os.path.exists(COOKIES_FILE):
        return {"cookiefile": COOKIES_FILE}
    print("⚠️ cookies.txt չկա — YouTube-ը կարող է սահմանափակել")
    return {}

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չկա")

ADMIN_ID = 7304274135

# RapidAPI — Social Download All-in-One
RAPIDAPI_KEY = "84c6910a82mshb9fff0a8c0c62f1p109a93jsn9ce6c2818c4c"
RAPIDAPI_HOST = "social-download-all-in-one.p.rapidapi.com"
RAPIDAPI_URL = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"

RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/json",
}

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

PINTEREST_REGEX = re.compile(
    r'(https?://)?(www\.|[a-z]{2}\.)?pinterest\.(com|co\.[a-z]+)/pin/[\w\-]+'
)

INSTAGRAM_PHOTO_REGEX = re.compile(
    r'(https?://)?(www\.)?instagram\.com/p/[\w\-]+'
)

def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = has_ffmpeg()
print(f"ffmpeg: {'✅ կա' if FFMPEG_AVAILABLE else '❌ չկա'}")
print(f"cookies.txt: {'✅ կա' if os.path.exists(COOKIES_FILE) else '❌ չկա'}")

# ─────────────────────────────
# RAPIDAPI — Universal Social Downloader
# TikTok, Instagram, Pinterest-ի համար
# ─────────────────────────────

def rapidapi_download(url):
    """
    RapidAPI Social Download All-in-One-ով ներբեռնում։
    Վերադարձնում է (file_path, tmp_dir, title) կամ (None, tmp_dir, None)
    """
    tmp_dir = tempfile.mkdtemp()
    title = "Media"

    try:
        resp = requests.post(
            RAPIDAPI_URL,
            headers=RAPIDAPI_HEADERS,
            json={"url": url},
            timeout=30,
        )
        data = resp.json()
        print("RAPIDAPI RESPONSE:", data)

        # title-ն
        title = data.get("title") or data.get("desc") or "Media"

        # Medias-ի ցուցակ
        medias = data.get("medias") or []

        if not medias:
            print("⚠️ RapidAPI — medias դատարկ է")
            return None, tmp_dir, None

        # Ընտրել լավագույն մեդիան
        # Նախ փնտրում ենք mp4 video, հետո audio, հետո image
        chosen = None
        for quality in ["hd", "sd", "audio", "thumbnail"]:
            for m in medias:
                if m.get("quality") == quality and m.get("url"):
                    chosen = m
                    break
            if chosen:
                break

        # Եթե quality-ով չգտանք — առաջինն ենք վերցնում
        if not chosen:
            for m in medias:
                if m.get("url"):
                    chosen = m
                    break

        if not chosen:
            print("⚠️ RapidAPI — ներբեռնելի URL չկա")
            return None, tmp_dir, None

        media_url = chosen["url"]
        ext = chosen.get("extension") or chosen.get("ext") or "mp4"
        if not ext.startswith("."):
            ext = f".{ext}"

        # Ներբեռնել ֆայլը
        file_resp = requests.get(media_url, timeout=60, stream=True)
        file_resp.raise_for_status()

        # Ֆայլի ընդլայնումը content-type-ից
        ct = file_resp.headers.get("content-type", "")
        if "jpeg" in ct or "jpg" in ct:
            ext = ".jpg"
        elif "png" in ct:
            ext = ".png"
        elif "webp" in ct:
            ext = ".webp"
        elif "mp4" in ct or "video" in ct:
            ext = ".mp4"
        elif "audio" in ct or "mpeg" in ct:
            ext = ".mp3"

        safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip() or "media"
        file_path = os.path.join(tmp_dir, f"{safe_title}{ext}")

        with open(file_path, "wb") as f:
            for chunk in file_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ RapidAPI ներբեռնեց՝ {file_path}")
        return file_path, tmp_dir, title

    except Exception as e:
        print("RAPIDAPI ERROR:", e)
        return None, tmp_dir, None


# ─────────────────────────────
# START / HELP
# ─────────────────────────────

WELCOME_IMAGE_URL = "https://i.imgur.com/4M34hi2.png"

@bot.message_handler(commands=['start', 'help'])
def start(message):
    users.add(message.from_user.id)

    welcome_text = (
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն — Որոնել\n"
        "🎧 /download երգի անուն — Ներբեռնել\n"
        "🔗 YouTube հղում — Audio ներբեռնել\n"
        "🎵 TikTok հղում — Վիդեո ներբեռնել\n"
        "📸 Instagram հղում — Վիդեո/նկար ներբեռնել\n"
        "📌 Pinterest հղում — Նկար/վիդեո ներբեռնել\n"
        "➕ /add երգի անուն — Պլեյլիստ ավելացնել\n"
        "📋 /playlist — Պլեյլիստ տեսնել\n"
        "🗑 /remove համար — Հեռացնել\n"
        "🔄 /update — Թարմացնել yt-dlp"
    )

    try:
        bot.send_photo(message.chat.id, photo=WELCOME_IMAGE_URL, caption=welcome_text)
    except Exception:
        bot.send_message(message.chat.id, welcome_text)

# ─────────────────────────────
# UPDATE
# ─────────────────────────────

@bot.message_handler(commands=['update'])
def update_command(message):
    users.add(message.from_user.id)
    msg = bot.send_message(message.chat.id, "🔄 Թարմացնում եմ yt-dlp...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            check=True, capture_output=True, text=True
        )
        global FFMPEG_AVAILABLE
        FFMPEG_AVAILABLE = has_ffmpeg()
        version = yt_dlp.version.__version__
        cookies_status = "✅ կա" if os.path.exists(COOKIES_FILE) else "❌ չկա"
        bot.edit_message_text(
            f"✅ yt-dlp թարմացվեց\n"
            f"📦 Տարբերակ: {version}\n"
            f"🔧 ffmpeg: {'✅ կա' if FFMPEG_AVAILABLE else '❌ չկա'}\n"
            f"🍪 cookies.txt: {cookies_status}",
            message.chat.id, msg.message_id
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Ձախողվեց\n{e}", message.chat.id, msg.message_id)

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

    try:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "skip_download": True,
            **get_cookies_opts(),
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
            f"🎵 {title}\n⏱ {mins}:{secs:02d}\n🔗 {url}"
        )

    except Exception as e:
        print("SEARCH ERROR:", e)
        bot.send_message(message.chat.id, f"❌ Չգտնվեց\n⚠️ {str(e)[:150]}")

# ─────────────────────────────
# YOUTUBE — Audio Download (yt-dlp)
# ─────────────────────────────

def download_audio(query_or_url):
    tmp_dir = tempfile.mkdtemp()
    is_url = bool(YOUTUBE_REGEX.match(query_or_url.strip()))
    source = query_or_url.strip() if is_url else f"ytsearch1:{query_or_url}"
    title = "Անհայտ"

    try:
        if FFMPEG_AVAILABLE:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }],
                **get_cookies_opts(),
            }
        else:
            ydl_opts = {
                "format": "140/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
                "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
                **get_cookies_opts(),
            }

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

        print("FILES IN TMP:", os.listdir(tmp_dir))
        return None, tmp_dir, None

    except Exception as e:
        print("DOWNLOAD ERROR:", e)
        return None, tmp_dir, None


# ─────────────────────────────
# YOUTUBE — Video Download (yt-dlp)
# ─────────────────────────────

def download_youtube_video(url):
    """YouTube վիդեո ներբեռնում mp4 ֆորմատով"""
    tmp_dir = tempfile.mkdtemp()
    title = "Անհայտ"

    try:
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            **get_cookies_opts(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = info.get("title", "Անհայտ")

        for f in os.listdir(tmp_dir):
            if f.endswith((".mp4", ".mov", ".webm", ".mkv")):
                return os.path.join(tmp_dir, f), tmp_dir, title

        print("FILES IN TMP:", os.listdir(tmp_dir))
        return None, tmp_dir, None

    except Exception as e:
        print("YOUTUBE VIDEO ERROR:", e)
        return None, tmp_dir, None


# ─────────────────────────────
# UTILS
# ─────────────────────────────

def cleanup(tmp_dir):
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except:
        pass


def send_audio_file(chat_id, file_path, title, msg_id):
    with open(file_path, "rb") as audio:
        bot.send_audio(chat_id, audio, title=title, performer="🎵 YouTube")
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass


def send_video_file(chat_id, file_path, title, msg_id, platform=""):
    with open(file_path, "rb") as video:
        bot.send_video(chat_id, video, caption=f"{platform} {title}")
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass


def send_media_file(chat_id, file_path, title, msg_id, platform=""):
    """Ինքնաբերաբար ճանաչում է ֆայլի տեսակը և ուղարկում"""
    try:
        if file_path.endswith((".jpg", ".jpeg", ".png", ".webp")):
            with open(file_path, "rb") as photo:
                bot.send_photo(chat_id, photo, caption=f"{platform} {title}")
        else:
            with open(file_path, "rb") as video:
                bot.send_video(chat_id, video, caption=f"{platform} {title}")
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    except Exception as e:
        print("SEND MEDIA ERROR:", e)


# ─────────────────────────────
# DOWNLOAD COMMAND (/download)
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
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update և կրկնիր",
            message.chat.id, msg.message_id
        )

    cleanup(tmp_dir)


# ─────────────────────────────
# YOUTUBE URL — Audio + Video inline keyboard
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
def handle_youtube_url(message):
    users.add(message.from_user.id)
    url = YOUTUBE_REGEX.search(message.text).group(0)

    # Ընտրություն — Audio կամ Video
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"yt_audio|{url}"),
        telebot.types.InlineKeyboardButton("🎬 Video (MP4)", callback_data=f"yt_video|{url}"),
    )
    bot.send_message(
        message.chat.id,
        "🔗 YouTube հղում — Ի՞նչ ներբեռնել?",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("yt_audio|") or call.data.startswith("yt_video|"))
def youtube_callback(call):
    bot.answer_callback_query(call.id)
    action, url = call.data.split("|", 1)

    if action == "yt_audio":
        msg = bot.send_message(call.message.chat.id, "🎵 Audio ներբեռնում եմ...")
        file_path, tmp_dir, title = download_audio(url)
        if file_path and os.path.exists(file_path):
            bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", call.message.chat.id, msg.message_id)
            send_audio_file(call.message.chat.id, file_path, title, msg.message_id)
        else:
            bot.edit_message_text(
                "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update",
                call.message.chat.id, msg.message_id
            )
        cleanup(tmp_dir)

    elif action == "yt_video":
        msg = bot.send_message(call.message.chat.id, "🎬 Video ներբեռնում եմ...")
        file_path, tmp_dir, title = download_youtube_video(url)
        if file_path and os.path.exists(file_path):
            bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", call.message.chat.id, msg.message_id)
            send_video_file(call.message.chat.id, file_path, title, msg.message_id, "🎬 YouTube")
        else:
            bot.edit_message_text(
                "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update",
                call.message.chat.id, msg.message_id
            )
        cleanup(tmp_dir)


# ─────────────────────────────
# TIKTOK URL — RapidAPI
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(TIKTOK_REGEX.search(m.text or "")))
def handle_tiktok_url(message):
    users.add(message.from_user.id)
    url = TIKTOK_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "🎵 TikTok հղում, ներբեռնում եմ...")

    # Փորձ 1 — RapidAPI
    file_path, tmp_dir, title = rapidapi_download(url)

    # Փորձ 2 — yt-dlp fallback
    if not file_path or not os.path.exists(file_path):
        print("TikTok RapidAPI failed, trying yt-dlp...")
        cleanup(tmp_dir)
        tmp_dir2 = tempfile.mkdtemp()
        try:
            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": f"{tmp_dir2}/%(title)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    title = info.get("title", "TikTok")
            for f in os.listdir(tmp_dir2):
                if f.endswith((".mp4", ".mov", ".webm", ".mkv")):
                    file_path = os.path.join(tmp_dir2, f)
                    tmp_dir = tmp_dir2
                    break
        except Exception as e:
            print("TikTok yt-dlp ERROR:", e)
            tmp_dir = tmp_dir2

    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_media_file(message.chat.id, file_path, title, msg.message_id, "🎵 TikTok")
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update և կրկնիր",
            message.chat.id, msg.message_id
        )

    cleanup(tmp_dir)


# ─────────────────────────────
# INSTAGRAM URL — RapidAPI
# /p/ → նկար;  /reel/ կամ /tv/ → վիդեո
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(INSTAGRAM_REGEX.search(m.text or "")))
def handle_instagram_url(message):
    users.add(message.from_user.id)
    url = INSTAGRAM_REGEX.search(message.text).group(0)
    is_photo = bool(INSTAGRAM_PHOTO_REGEX.match(url))

    emoji = "📸 Instagram նկար" if is_photo else "📸 Instagram Reel"
    msg = bot.send_message(message.chat.id, f"{emoji}, ներբեռնում եմ...")

    # Փորձ 1 — RapidAPI
    file_path, tmp_dir, title = rapidapi_download(url)

    # Փորձ 2 — yt-dlp fallback
    if not file_path or not os.path.exists(file_path):
        print("Instagram RapidAPI failed, trying yt-dlp...")
        cleanup(tmp_dir)
        tmp_dir2 = tempfile.mkdtemp()
        try:
            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": f"{tmp_dir2}/ig_%(id)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
                "http_headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                        "Version/16.0 Mobile/15E148 Safari/604.1"
                    ),
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    title = info.get("title", "Instagram")
            for f in os.listdir(tmp_dir2):
                if f.endswith((".mp4", ".mov", ".webm", ".mkv", ".jpg", ".jpeg", ".png")):
                    file_path = os.path.join(tmp_dir2, f)
                    tmp_dir = tmp_dir2
                    break
        except Exception as e:
            print("Instagram yt-dlp ERROR:", e)
            tmp_dir = tmp_dir2

    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_media_file(message.chat.id, file_path, title, msg.message_id, "📸 Instagram")
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n"
            "💡 Instagram-ը կարող է փակ լինել կամ հղումը սխալ է",
            message.chat.id, msg.message_id
        )

    cleanup(tmp_dir)


# ─────────────────────────────
# PINTEREST URL — RapidAPI
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(PINTEREST_REGEX.search(m.text or "")))
def handle_pinterest_url(message):
    users.add(message.from_user.id)
    url = PINTEREST_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "📌 Pinterest հղում, ներբեռնում եմ...")

    # Փորձ 1 — RapidAPI
    file_path, tmp_dir, title = rapidapi_download(url)

    # Փորձ 2 — yt-dlp fallback
    if not file_path or not os.path.exists(file_path):
        print("Pinterest RapidAPI failed, trying yt-dlp...")
        cleanup(tmp_dir)
        tmp_dir2 = tempfile.mkdtemp()
        try:
            ydl_opts = {
                "format": "best",
                "outtmpl": f"{tmp_dir2}/pin_%(id)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    title = info.get("title", "Pinterest")
            for f in os.listdir(tmp_dir2):
                if f.endswith((".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm")):
                    file_path = os.path.join(tmp_dir2, f)
                    tmp_dir = tmp_dir2
                    break
        except Exception as e:
            print("Pinterest yt-dlp ERROR:", e)
            tmp_dir = tmp_dir2

    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_media_file(message.chat.id, file_path, title, msg.message_id, "📌 Pinterest")
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update և կրկնիր",
            message.chat.id, msg.message_id
        )

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
    uid = message.from_user.id
    playlists.setdefault(uid, []).append(parts[1])
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
bot.polling(none_stop=True).
