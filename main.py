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
    for pkg in ["yt-dlp", "gallery-dl"]:
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

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8665023673:AAG96HlfGh0Yj8Jj6P1_Yvj5N_bWIiobp54")

ADMIN_ID = 7304274135

bot = telebot.TeleBot(TOKEN)
playlists = {}  # {user_id: [(title, file_path)]}
users = set()

WELCOME_IMAGE_URL = "https://i.ibb.co/wFSQWyb8/IMG-20260427-194624-991.jpg"

TIKTOK_REGEX = re.compile(
    r'(https?://)?(www\.|vm\.|vt\.)?(tiktok\.com/)[\S]+'
)
INSTAGRAM_REGEX = re.compile(
    r'(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+'
)

def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = has_ffmpeg()
print(f"ffmpeg: {'✅' if FFMPEG_AVAILABLE else '❌'}")

# Playlist ֆայլերի թղթապանակ
PLAYLIST_DIR = "/tmp/playlists"
os.makedirs(PLAYLIST_DIR, exist_ok=True)

# ─────────────────────────────
# START / HELP
# ─────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    users.add(message.from_user.id)
    text = (
        "🎵 Բարի գալուստ Yandeks Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն — Որոնել\n"
        "🎧 /download երգի անուն — Ներբեռնել\n"
        "🎵 TikTok հղում — Վիդեո ներբեռնել\n"
        "📸 Instagram հղում — Վիդեո ներբեռնել\n"
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
# YOUTUBE DOWNLOAD (փոխված Yandex-ից)
# ─────────────────────────────

def download_from_youtube(query, tmp_dir):
    """YouTube-ից ներբեռնում"""
    title = "Անհայտ"
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": False,
            "socket_timeout": 30,
            "retries": 3,
        }
        if FFMPEG_AVAILABLE:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        # ✅ ytsearch — YouTube-ից, login չի պահանջում
        source = f"ytsearch1:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source, download=True)
            if info and "entries" in info and info["entries"]:
                title = info["entries"][0].get("title", "Անհայտ")
            elif info:
                title = info.get("title", "Անհայտ")

        for f in os.listdir(tmp_dir):
            if f.endswith((".mp3", ".m4a", ".webm", ".ogg", ".opus")):
                print(f"✅ YouTube: {title}")
                return os.path.join(tmp_dir, f), title

    except Exception as e:
        print(f"YouTube download failed: {e}")

    return None, title

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
    bot.send_message(message.chat.id, "🔍 Որոնում եմ YouTube-ում...")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True, "skip_download": True}) as ydl:
            # ✅ ytsearch3 — YouTube
            info = ydl.extract_info(f"ytsearch3:{query}", download=False)
        if not info or "entries" not in info or not info["entries"]:
            bot.send_message(message.chat.id, "❌ Չգտնվեց")
            return
        text = "🎵 YouTube-ում գտնվեց՝\n\n"
        for i, entry in enumerate(info["entries"][:3], 1):
            title = entry.get("title", "Անհայտ")
            duration = entry.get("duration", 0) or 0
            mins, secs = divmod(int(duration), 60)
            text += f"{i}. 🎵 {title} ({mins}:{secs:02d})\n"
        bot.send_message(message.chat.id, text)
    except Exception as e:
        print(f"SEARCH ERROR: {e}")
        bot.send_message(message.chat.id, "❌ Չգտնվեց")

# ─────────────────────────────
# DOWNLOAD
# ─────────────────────────────

@bot.message_handler(commands=['download'])
def download(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգի անուն")
        return
    query = parts[1]
    msg = bot.send_message(message.chat.id, "⏳ YouTube-ից ներբեռնում եմ...")
    tmp_dir = tempfile.mkdtemp()
    file_path, title = download_from_youtube(query, tmp_dir)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
        with open(file_path, "rb") as audio:
            bot.send_audio(message.chat.id, audio, title=title, performer="🎵 YouTube")
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    # Cleanup
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass

# ─────────────────────────────
# TIKTOK
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(TIKTOK_REGEX.search(m.text or "")))
def handle_tiktok(message):
    users.add(message.from_user.id)
    url = TIKTOK_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "🎵 TikTok, ներբեռնում եմ...")
    tmp_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "gallery_dl", url, "-D", tmp_dir],
            capture_output=True, text=True, timeout=60
        )
        files = sorted(os.listdir(tmp_dir))
        if files:
            f = files[0]
            file_path = os.path.join(tmp_dir, f)
            title = f.rsplit(".", 1)[0]
            bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
            ext = f.lower().rsplit(".", 1)[-1]
            if ext in ("jpg", "jpeg", "png", "webp"):
                with open(file_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=f"🎵 {title}")
            else:
                with open(file_path, "rb") as video:
                    bot.send_video(message.chat.id, video, caption=f"🎵 {title}")
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass
        else:
            bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    except Exception as e:
        print(f"TikTok error: {e}")
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass

# ─────────────────────────────
# INSTAGRAM
# ─────────────────────────────

@bot.message_handler(func=lambda m: bool(INSTAGRAM_REGEX.search(m.text or "")))
def handle_instagram(message):
    users.add(message.from_user.id)
    url = INSTAGRAM_REGEX.search(message.text).group(0)
    msg = bot.send_message(message.chat.id, "📸 Instagram, ներբեռնում եմ...")
    tmp_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "gallery_dl", url, "-D", tmp_dir],
            capture_output=True, text=True, timeout=60
        )
        files = sorted(os.listdir(tmp_dir))
        if files:
            f = files[0]
            file_path = os.path.join(tmp_dir, f)
            title = f.rsplit(".", 1)[0]
            bot.edit_message_text(f"📤 Ուղարկում եմ՝ {title}", message.chat.id, msg.message_id)
            ext = f.lower().rsplit(".", 1)[-1]
            if ext in ("jpg", "jpeg", "png", "webp"):
                with open(file_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=f"📸 {title}")
            else:
                with open(file_path, "rb") as video:
                    bot.send_video(message.chat.id, video, caption=f"📸 {title}")
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass
        else:
            bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    except Exception as e:
        print(f"Instagram error: {e}")
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass

# ─────────────────────────────
# PLAYLIST — MP3 ֆայլերով
# ─────────────────────────────

@bot.message_handler(commands=['add'])
def add(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /add երգի անուն")
        return
    query = parts[1]
    uid = message.from_user.id
    msg = bot.send_message(message.chat.id, f"⏳ Ավելացնում եմ՝ {query}...")

    tmp_dir = tempfile.mkdtemp()
    file_path, title = download_from_youtube(query, tmp_dir)

    if file_path and os.path.exists(file_path):
        # Պահել playlist թղթապանակում
        user_dir = os.path.join(PLAYLIST_DIR, str(uid))
        os.makedirs(user_dir, exist_ok=True)
        ext = file_path.rsplit(".", 1)[-1]
        save_path = os.path.join(user_dir, f"{len(playlists.get(uid, []))}.{ext}")
        os.rename(file_path, save_path)

        playlists.setdefault(uid, []).append((title, save_path))
        bot.edit_message_text(f"✅ Ավելացվեց՝ 🎵 {title}", message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ Չստացվեց գտնել երգը", message.chat.id, msg.message_id)

    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass


@bot.message_handler(commands=['playlist'])
def playlist(message):
    users.add(message.from_user.id)
    uid = message.from_user.id
    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Դատարկ է")
        return
    text = "📋 Քո պլեյլիստը՝\n\n"
    for i, (title, _) in enumerate(playlists[uid], 1):
        text += f"{i}. 🎵 {title}\n"
    text += "\n🎵 Ուղարկե՞մ բոլոր երգերը — գրիր /playall"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['playall'])
def playall(message):
    users.add(message.from_user.id)
    uid = message.from_user.id
    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Դատարկ է")
        return
    bot.send_message(message.chat.id, f"🎵 Ուղարկում եմ {len(playlists[uid])} երգ...")
    for title, file_path in playlists[uid]:
        try:
            if os.path.exists(file_path):
                with open(file_path, "rb") as audio:
                    bot.send_audio(message.chat.id, audio, title=title, performer="🎵 YouTube")
            else:
                bot.send_message(message.chat.id, f"❌ {title} — ֆայլը չկա")
        except Exception as e:
            print(f"playall error: {e}")


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
        title, file_path = playlists[uid].pop(idx)
        try:
            os.remove(file_path)
        except:
            pass
        bot.send_message(message.chat.id, f"🗑 Ջնջվեց՝ {title}")
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
