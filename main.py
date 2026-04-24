import os
import tempfile

import telebot
import yt_dlp


# ─────────────────────────────
# CONFIG
# ─────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise Exception("TELEGRAM_BOT_TOKEN չկա environment-ում")

bot = telebot.TeleBot(TOKEN)

playlists = {}


# ─────────────────────────────
# DOWNLOAD CORE
# ─────────────────────────────

def download_audio(query):
    tmp_dir = tempfile.mkdtemp()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
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


def cleanup(tmp_dir):
    try:
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)
    except:
        pass


# ─────────────────────────────
# COMMANDS
# ─────────────────────────────

@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎵 Երգի Բոտ\n\n"
        "/search երգ\n"
        "/download երգ\n"
        "/add երգ\n"
        "/playlist\n"
        "/remove համար"
    )


@bot.message_handler(commands=["download"])
def download(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "Գրիր երգի անուն")
        return

    query = parts[1]

    msg = bot.send_message(message.chat.id, "⏳ Ներբեռնում եմ...")

    file_path, tmp_dir = download_audio(query)

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as audio:
                bot.send_audio(message.chat.id, audio)

            bot.delete_message(message.chat.id, msg.message_id)

        except Exception as e:
            bot.edit_message_text(f"❌ Սխալ: {e}", message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)

    cleanup(tmp_dir)


@bot.message_handler(commands=["search"])
def search(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "Գրիր երգ")
        return

    query = parts[1]

    try:
        import subprocess

        result = subprocess.run(
            ["python", "-m", "yt_dlp", f"ytsearch1:{query}", "--get-title"],
            capture_output=True,
            text=True,
        )

        title = result.stdout.strip()

        bot.send_message(message.chat.id, f"🎵 {title}")

    except:
        bot.send_message(message.chat.id, "❌ Չգտնվեց")


@bot.message_handler(commands=["add"])
def add(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        return

    uid = message.from_user.id
    playlists.setdefault(uid, []).append(parts[1])

    bot.send_message(message.chat.id, "✅ Ավելացվեց")


@bot.message_handler(commands=["playlist"])
def playlist(message):
    uid = message.from_user.id

    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Դատարկ է")
        return

    text = "📋 Պլեյլիստ\n\n"

    for i, s in enumerate(playlists[uid], 1):
        text += f"{i}. {s}\n"

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["remove"])
def remove(message):
    parts = message.text.split(maxsplit=1)
    uid = message.from_user.id

    if len(parts) < 2 or not parts[1].isdigit():
        return

    idx = int(parts[1]) - 1

    if uid in playlists and 0 <= idx < len(playlists[uid]):
        playlists[uid].pop(idx)

    bot.send_message(message.chat.id, "🗑 Ջնջվեց")


@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.send_message(message.chat.id, "❓ /help")


# ─────────────────────────────

print("BOT RUNNING")
bot.polling(none_stop=True)
