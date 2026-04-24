import os
import tempfile

import telebot
import yt_dlp


# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չկա")

bot = telebot.TeleBot(TOKEN)

playlists = {}


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
        "➕ /add երգի անուն — Ավելացնել պլեյլիստ\n"
        "📋 /playlist — Տեսնել պլեյլիստը\n"
        "🗑 /remove համար — Հեռացնել պլեյլիստից"
    )


# ─────────────────────────────
# SEARCH
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
        ydl = yt_dlp.YoutubeDL({"quiet": True})

        info = ydl.extract_info(f"ytsearch1:{query}", download=False)

        if "entries" in info:
            info = info["entries"][0]

        title = info.get("title")
        url = info.get("webpage_url")

        bot.send_message(message.chat.id, f"🎵 {title}\n🔗 {url}")

    except:
        bot.send_message(message.chat.id, "❌ Չգտնվեց")


# ─────────────────────────────
# DOWNLOAD (MP3)
# ─────────────────────────────

def download_audio(query):
    tmp_dir = tempfile.mkdtemp()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(f"ytsearch1:{query}", download=True)

        for f in os.listdir(tmp_dir):
            if f.endswith(".mp3"):
                return os.path.join(tmp_dir, f), tmp_dir

        return None, tmp_dir

    except Exception as e:
        print("ERROR:", e)
        return None, tmp_dir


@bot.message_handler(commands=['download'])
def download(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգի անուն")
        return

    query = parts[1]

    msg = bot.send_message(message.chat.id, "⏳ Ներբեռնում եմ...")

    file_path, tmp_dir = download_audio(query)

    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as audio:
            bot.send_audio(message.chat.id, audio)

        bot.delete_message(message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)

    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass


# ─────────────────────────────
# PLAYLIST ADD
# ─────────────────────────────

@bot.message_handler(commands=['add'])
def add(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /add երգ")
        return

    uid = message.from_user.id
    playlists.setdefault(uid, []).append(parts[1])

    bot.send_message(message.chat.id, "✅ Ավելացվեց")


# ─────────────────────────────
# PLAYLIST SHOW
# ─────────────────────────────

@bot.message_handler(commands=['playlist'])
def playlist(message):
    uid = message.from_user.id

    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Դատարկ է")
        return

    text = "📋 Քո պլեյլիստը՝\n\n"

    for i, s in enumerate(playlists[uid], 1):
        text += f"{i}. 🎵 {s}\n"

    bot.send_message(message.chat.id, text)


# ─────────────────────────────
# REMOVE
# ─────────────────────────────

@bot.message_handler(commands=['remove'])
def remove(message):
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
    bot.send_message(message.chat.id, "❓ Գրիր /help")


# ─────────────────────────────

print("✅ BOT RUNNING...")
bot.polling(none_stop=True)
