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

ADMIN_ID = 7304274135  # ← Քո Telegram ID-ն դիր այստեղ (@userinfobot-ից ստացիր)

bot = telebot.TeleBot(TOKEN)
playlists = {}
users = set()  # Բոլոր օգտատերերի ID-ները

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)

TIKTOK_REGEX = re.compile(
    r'(https?://)?(www\.|vm\.|vt\.)?(tiktok\.com/)[\S]+'
)

INSTAGRAM_REGEX = re.compile(
    r'(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+'
)

# ─── ՆՈՐ: Pinterest regex ───
PINTEREST_REGEX = re.compile(
    r'(https?://)?(www\.|[a-z]{2}\.)?pinterest\.(com|co\.[a-z]+)/pin/[\w\-]+'
)

# ─── ՆՈՐ: Instagram նկարի regex (միայն /p/ — ոչ reel/tv) ───
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

# ─────────────────────────────
# START / HELP  ← ՆՈՐ: ուղարկում է նկար
# ─────────────────────────────

WELCOME_IMAGE_URL = "https://i.imgur.com/4M34hi2.png"  # ← Փոխիր քո ուզած նկարի URL-ով

@bot.message_handler(commands=['start', 'help'])
def start(message):
    users.add(message.from_user.id)

    welcome_text = (
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
        "🔄 /update — Թարմացնել yt-dlp"
    )

    try:
        bot.send_photo(
            message.chat.id,
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text
        )
    except Exception:
        # Եթե նկարը չբեռնվի — ուղարկիր սովորական տեքստ
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
        bot.edit_message_text(
            f"✅ yt-dlp թարմացվեց\n"
            f"📦 Տարբերակ: {version}\n"
            f"🔧 ffmpeg: {'✅ կա' if FFMPEG_AVAILABLE else '❌ չկա'}",
            message.chat.id, msg.message_id
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Ձախողվեց\n{e}", message.chat.id, msg.message_id)

# ─────────────────────────────
# BROADCAST — միայն ադմինի համար
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
        f"✅ Ուղարկվեց {success} հոգու\n"
        f"❌ Չստացվեց {failed} հոգու",
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
# DOWNLOAD CORE (Audio — YouTube)
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
            }
        else:
            ydl_opts = {
                "format": "140/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
                "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
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
# VIDEO DOWNLOAD (TikTok / Instagram)
# ─────────────────────────────

def download_video(url):
    tmp_dir = tempfile.mkdtemp()
    title = "Անհայտ"

    try:
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
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
        print("VIDEO DOWNLOAD ERROR:", e)
        return None, tmp_dir, None

# ─── ՆՈՐ: PHOTO DOWNLOAD (Instagram նկար / Pinterest) ───

def download_photo(url):
    """Ներբեռնում է նկար՝ yt-dlp-ի միջոցով (Instagram photo, Pinterest)"""
    tmp_dir = tempfile.mkdtemp()
    title = "Անհայտ"

    try:
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "writethumbnail": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = info.get("title", "Անհայտ")

        # Փնտրում ենք բոլոր հնարավոր ֆայլերը
        for f in os.listdir(tmp_dir):
            if f.endswith((".jpg", ".jpeg", ".png", ".webp",
                           ".mp4", ".mov", ".webm", ".mkv")):
                return os.path.join(tmp_dir, f), tmp_dir, title

        print("FILES IN TMP:", os.listdir(tmp_dir))
        return None, tmp_dir, None

    except Exception as e:
        print("PHOTO DOWNLOAD ERROR:", e)
        return None, tmp_dir, None


def cleanup(tmp_dir):
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
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


# ─── ՆՈՐ: send_media_file — ուղարկում է նկար կամ վիդեո ───

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
# DOWNLOAD COMMAND
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
# YOUTUBE URL
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
def handle_youtube_url(message):
    users.add(message.from_user.id)
    url = YOUTUBE_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "🔗 YouTube հղում, ներբեռնում եմ...")

    file_path, tmp_dir, title = download_audio(url)

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
# TIKTOK URL
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(TIKTOK_REGEX.search(m.text or "")))
def handle_tiktok_url(message):
    users.add(message.from_user.id)
    url = TIKTOK_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "🎵 TikTok հղում, ներբեռնում եմ...")

    file_path, tmp_dir, title = download_video(url)

    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        send_video_file(message.chat.id, file_path, title, msg.message_id, "🎵 TikTok")
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update և կրկնիր",
            message.chat.id, msg.message_id
        )

    cleanup(tmp_dir)

# ─────────────────────────────
# INSTAGRAM URL  ← ՆՈՐ ՏՐԱՄԱԲԱՆՈՒԹՅՈՒՆ
# /p/ → նկար;  /reel/ կամ /tv/ → վիդեո
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(INSTAGRAM_REGEX.search(m.text or "")))
def handle_instagram_url(message):
    users.add(message.from_user.id)
    url = INSTAGRAM_REGEX.search(message.text).group(0)

    # Ստուգում՝ նկա՞ր, թե՞ վիդեո
    is_photo = bool(INSTAGRAM_PHOTO_REGEX.match(url))

    if is_photo:
        msg = bot.send_message(message.chat.id, "📸 Instagram նկար, ներբեռնում եմ...")
        file_path, tmp_dir, title = download_photo(url)
        if file_path and os.path.exists(file_path):
            bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
            send_media_file(message.chat.id, file_path, title, msg.message_id, "📸 Instagram")
        else:
            bot.edit_message_text(
                "❌ Չստացվեց ներբեռնել\n💡 Instagram-ը կարող է փակ լինել",
                message.chat.id, msg.message_id
            )
        cleanup(tmp_dir)
    else:
        msg = bot.send_message(message.chat.id, "📸 Instagram հղում, ներբեռնում եմ...")
        file_path, tmp_dir, title = download_video(url)
        if file_path and os.path.exists(file_path):
            bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
            send_video_file(message.chat.id, file_path, title, msg.message_id, "📸 Instagram")
        else:
            bot.edit_message_text(
                "❌ Չստացվեց ներբեռնել\n💡 Փորձիր /update և կրկնիր",
                message.chat.id, msg.message_id
            )
        cleanup(tmp_dir)

# ─────────────────────────────
# ՆՈՐ: PINTEREST URL
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(PINTEREST_REGEX.search(m.text or "")))
def handle_pinterest_url(message):
    users.add(message.from_user.id)
    url = PINTEREST_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "📌 Pinterest հղում, ներբեռնում եմ...")

    file_path, tmp_dir, title = download_photo(url)

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
bot.polling(none_stop=True)
