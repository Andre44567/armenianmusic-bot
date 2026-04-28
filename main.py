import os
import tempfile
import re
import subprocess
import sys
import urllib.request
import urllib.parse
import json

import telebot

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
            print(f"OK: {pkg}")
        except Exception as e:
            print(f"WARN: {pkg}: {e}")

install_deps()

# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8665023673:AAG96HlfGh0Yj8Jj6P1_Yvj5N_bWIiobp54")
ADMIN_ID = 7304274135

bot = telebot.TeleBot(TOKEN)
playlists = {}
users = set()

WELCOME_IMAGE_URL = "https://i.ibb.co/wFSQWyb8/IMG-20260427-194624-991.jpg"

TIKTOK_REGEX = re.compile(r'(https?://)?(www\.|vm\.|vt\.)?(tiktok\.com/)[\S]+')
INSTAGRAM_REGEX = re.compile(r'(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+')

PLAYLIST_DIR = "/tmp/playlists"
os.makedirs(PLAYLIST_DIR, exist_ok=True)

# ─────────────────────────────
# DEEZER
# ─────────────────────────────

def deezer_search(query, limit=3):
    url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit={limit}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read()).get("data", [])

def download_from_deezer(query, tmp_dir):
    title = "Unknown"
    try:
        tracks = deezer_search(query, limit=1)
        if not tracks:
            return None, title

        track = tracks[0]
        artist = track.get("artist", {}).get("name", "")
        name = track.get("title", "Unknown")
        title = f"{artist} - {name}"
        preview_url = track.get("preview", "")

        if not preview_url:
            return None, title

        file_path = os.path.join(tmp_dir, "track.mp3")
        urllib.request.urlretrieve(preview_url, file_path)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"OK Deezer: {title}")
            return file_path, title

    except Exception as e:
        print(f"Deezer error: {e}")

    return None, title

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
        "📋 /playlist — Պլեյлиst տеснел\n"
        "🗑 /remove համар — Hеռацнел\n"
        "🔄 /update — Tarmacnel\n\n"
        "⚠️ Deezer preview — 30 վайркyан"
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
    msg = bot.send_message(message.chat.id, "🔄 Updating...")
    install_deps()
    bot.edit_message_text("OK Updated", message.chat.id, msg.message_id)

# ─────────────────────────────
# BROADCAST
# ─────────────────────────────

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    users.add(message.from_user.id)
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "No access")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "/broadcast <text>")
        return
    text = parts[1]
    success = 0
    failed = 0
    for uid in users.copy():
        try:
            bot.send_message(uid, f"Broadcast: {text}")
            success += 1
        except Exception:
            failed += 1
    bot.send_message(message.chat.id, f"Sent: {success}, Failed: {failed}")

# ─────────────────────────────
# SEARCH
# ─────────────────────────────

@bot.message_handler(commands=['search'])
def search(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Write: /search song name")
        return
    query = parts[1]
    msg = bot.send_message(message.chat.id, "Searching Deezer...")
    try:
        tracks = deezer_search(query, limit=3)
        if not tracks:
            bot.edit_message_text("Not found", message.chat.id, msg.message_id)
            return
        text = "Results from Deezer:\n\n"
        for i, track in enumerate(tracks, 1):
            artist = track.get("artist", {}).get("name", "")
            name = track.get("title", "Unknown")
            duration = track.get("duration", 0)
            mins, secs = divmod(duration, 60)
            text += f"{i}. {artist} - {name} ({mins}:{secs:02d})\n"
        text += "\nNote: 30 second preview"
        bot.edit_message_text(text, message.chat.id, msg.message_id)
    except Exception as e:
        print(f"Search error: {e}")
        bot.edit_message_text("Error searching", message.chat.id, msg.message_id)

# ─────────────────────────────
# DOWNLOAD
# ─────────────────────────────

@bot.message_handler(commands=['download'])
def download(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Write: /download song name")
        return
    query = parts[1]
    msg = bot.send_message(message.chat.id, "Downloading from Deezer...")
    tmp_dir = tempfile.mkdtemp()
    file_path, title = download_from_deezer(query, tmp_dir)
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(f"Sending: {title}", message.chat.id, msg.message_id)
        with open(file_path, "rb") as audio:
            bot.send_audio(message.chat.id, audio, title=title, performer="Deezer")
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
    else:
        bot.edit_message_text("Download failed", message.chat.id, msg.message_id)
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
    msg = bot.send_message(message.chat.id, "TikTok downloading...")
    tmp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            [sys.executable, "-m", "gallery_dl", url, "-D", tmp_dir],
            capture_output=True, text=True, timeout=60
        )
        files = sorted(os.listdir(tmp_dir))
        if files:
            f = files[0]
            file_path = os.path.join(tmp_dir, f)
            title = f.rsplit(".", 1)[0]
            ext = f.lower().rsplit(".", 1)[-1]
            bot.edit_message_text(f"Sending: {title}", message.chat.id, msg.message_id)
            if ext in ("jpg", "jpeg", "png", "webp"):
                with open(file_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=title)
            else:
                with open(file_path, "rb") as video:
                    bot.send_video(message.chat.id, video, caption=title)
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass
        else:
            bot.edit_message_text("Download failed", message.chat.id, msg.message_id)
    except Exception as e:
        print(f"TikTok error: {e}")
        bot.edit_message_text("Download failed", message.chat.id, msg.message_id)
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
    msg = bot.send_message(message.chat.id, "Instagram downloading...")
    tmp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            [sys.executable, "-m", "gallery_dl", url, "-D", tmp_dir],
            capture_output=True, text=True, timeout=60
        )
        files = sorted(os.listdir(tmp_dir))
        if files:
            f = files[0]
            file_path = os.path.join(tmp_dir, f)
            title = f.rsplit(".", 1)[0]
            ext = f.lower().rsplit(".", 1)[-1]
            bot.edit_message_text(f"Sending: {title}", message.chat.id, msg.message_id)
            if ext in ("jpg", "jpeg", "png", "webp"):
                with open(file_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=title)
            else:
                with open(file_path, "rb") as video:
                    bot.send_video(message.chat.id, video, caption=title)
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass
        else:
            bot.edit_message_text("Download failed", message.chat.id, msg.message_id)
    except Exception as e:
        print(f"Instagram error: {e}")
        bot.edit_message_text("Download failed", message.chat.id, msg.message_id)
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass

# ─────────────────────────────
# PLAYLIST
# ─────────────────────────────

@bot.message_handler(commands=['add'])
def add(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Write: /add song name")
        return
    query = parts[1]
    uid = message.from_user.id
    msg = bot.send_message(message.chat.id, f"Adding: {query}...")
    tmp_dir = tempfile.mkdtemp()
    file_path, title = download_from_deezer(query, tmp_dir)
    if file_path and os.path.exists(file_path):
        user_dir = os.path.join(PLAYLIST_DIR, str(uid))
        os.makedirs(user_dir, exist_ok=True)
        save_path = os.path.join(user_dir, f"{len(playlists.get(uid, []))}.mp3")
        os.rename(file_path, save_path)
        playlists.setdefault(uid, []).append((title, save_path))
        bot.edit_message_text(f"Added: {title}", message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("Not found", message.chat.id, msg.message_id)
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
        bot.send_message(message.chat.id, "Playlist is empty")
        return
    text = "Your playlist:\n\n"
    for i, (title, _) in enumerate(playlists[uid], 1):
        text += f"{i}. {title}\n"
    text += "\nSend all — /playall"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['playall'])
def playall(message):
    users.add(message.from_user.id)
    uid = message.from_user.id
    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "Playlist is empty")
        return
    bot.send_message(message.chat.id, f"Sending {len(playlists[uid])} songs...")
    for title, file_path in playlists[uid]:
        try:
            if os.path.exists(file_path):
                with open(file_path, "rb") as audio:
                    bot.send_audio(message.chat.id, audio, title=title, performer="Deezer")
            else:
                bot.send_message(message.chat.id, f"File missing: {title}")
        except Exception as e:
            print(f"playall error: {e}")


@bot.message_handler(commands=['remove'])
def remove(message):
    users.add(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    uid = message.from_user.id
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "Write: /remove number")
        return
    idx = int(parts[1]) - 1
    if uid in playlists and 0 <= idx < len(playlists[uid]):
        title, file_path = playlists[uid].pop(idx)
        try:
            os.remove(file_path)
        except:
            pass
        bot.send_message(message.chat.id, f"Removed: {title}")
    else:
        bot.send_message(message.chat.id, "Wrong number")

# ─────────────────────────────
# FALLBACK
# ─────────────────────────────

@bot.message_handler(func=lambda m: True)
def unknown(message):
    users.add(message.from_user.id)
    bot.send_message(message.chat.id, "Write /help")

# ─────────────────────────────
print("BOT RUNNING...")
bot.polling(none_stop=True)
