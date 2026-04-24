import os
import tempfile
import traceback

import telebot
import yt_dlp


# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չկա")

bot = telebot.TeleBot(TOKEN)

playlists = {}


# ──────────────────────────────────────────────
# CORE FUNCTION (FIXED + DEBUG)
# ──────────────────────────────────────────────

def get_audio(query):
    tmp_dir = tempfile.mkdtemp()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": False,   # 🔥 ցույց է տալիս սխալները
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)

            if "entries" in info:
                info = info["entries"][0]

            title = info.get("title", "audio")

        files = os.listdir(tmp_dir)
        print("📂 TMP FILES:", files)

        for f in files:
            if f.endswith(".mp3"):
                return os.path.join(tmp_dir, f), tmp_dir, title

        return None, tmp_dir, None

    except Exception as e:
        print("❌ ERROR OCCURED:")
        traceback.print_exc()
        return None, tmp_dir, None


def cleanup(tmp_dir):
    if tmp_dir and os.path.exists(tmp_dir):
        for f in os.listdir(tmp_dir):
            try:
                os.remove(os.path.join(tmp_dir, f))
            except:
                pass
        try:
            os.rmdir(tmp_dir)
        except:
            pass


# ──────────────────────────────────────────────
# COMMANDS
# ──────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎵 Երգի Բոտ\n\n"
        "🔍 /search երգ\n"
        "🎧 /download երգ\n"
        "➕ /add երգ\n"
        "📋 /playlist\n"
        "🗑 /remove համար"
    )


@bot.message_handler(commands=["search"])
def search(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /search երգ")
        return

    query = parts[1]

    msg = bot.send_message(message.chat.id, "🔍 Որոնում եմ...")

    file_path, tmp_dir, title = get_audio(query)

    if title:
        bot.edit_message_text(f"🎵 {title}", message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ Չգտնվեց", message.chat.id, msg.message_id)

    cleanup(tmp_dir)


@bot.message_handler(commands=["download"])
def download(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգ")
        return

    query = parts[1]

    msg = bot.send_message(message.chat.id, "⏳ Ներբեռնում եմ...")

    file_path, tmp_dir, title = get_audio(query)

    if file_path and os.path.exists(file_path):
        try:
            bot.edit_message_text("📤 Ուղարկում եմ...", message.chat.id, msg.message_id)

            with open(file_path, "rb") as audio:
                bot.send_audio(message.chat.id, audio, caption=title)

            bot.delete_message(message.chat.id, msg.message_id)

        except Exception as e:
            bot.edit_message_text(
                f"❌ Ուղարկման սխալ:\n{e}",
                message.chat.id,
                msg.message_id
            )
    else:
        bot.edit_message_text(
            "❌ Չստացվեց ներբեռնել\n\n"
            "👉 Ստուգիր՝\n"
            "• yt-dlp տեղադրված է\n"
            "• ffmpeg կա համակարգում\n\n"
            "💡 Եթե error կա՝ կտեսնես console-ում",
            message.chat.id,
            msg.message_id
        )

    cleanup(tmp_dir)


@bot.message_handler(commands=["add"])
def add(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր երգ")
        return

    uid = message.from_user.id
    playlists.setdefault(uid, []).append(parts[1])

    bot.send_message(message.chat.id, "✅ Ա
