import os
import tempfile

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
# CORE FUNCTIONS
# ──────────────────────────────────────────────

def get_audio(query):
    tmp_dir = tempfile.mkdtemp()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)

            if 'entries' in info:
                info = info['entries'][0]

            title = info.get("title", "audio")
            webpage_url = info.get("webpage_url", "")

        for f in os.listdir(tmp_dir):
            if f.endswith(".mp3"):
                return os.path.join(tmp_dir, f), tmp_dir, title, webpage_url

        return None, tmp_dir, None, None

    except Exception as e:
        print("ERROR:", e)
        return None, tmp_dir, None, None


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

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎵 Բարի գալուստ Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն — Ստանալ հղում\n"
        "🎧 /download երգի անուն — Ներբեռնել MP3\n"
        "➕ /add երգ — Ավելացնել պլեյլիստ\n"
        "📋 /playlist — Իմ պլեյլիստը\n"
        "🗑 /remove համար — Ջնջել երգը"
    )


@bot.message_handler(commands=['search'])
def search(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /search երգի անուն")
        return

    query = parts[1]

    msg = bot.send_message(message.chat.id, "🔍 Որոնում եմ...")

    file_path, tmp_dir, title, link = get_audio(query)

    if link:
        bot.edit_message_text(
            f"🎵 {title}\n🔗 {link}",
            message.chat.id,
            msg.message_id
        )
    else:
        bot.edit_message_text("❌ Չգտնվեց", message.chat.id, msg.message_id)

    cleanup(tmp_dir)


@bot.message_handler(commands=['download'])
def download(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգի անուն")
        return

    query = parts[1]

    msg = bot.send_message(message.chat.id, "⏳ Ներբեռնում եմ...")

    file_path, tmp_dir, title, _ = get_audio(query)

    if file_path:
        try:
            bot.edit_message_text("📤 Ուղարկում եմ...", message.chat.id, msg.message_id)

            with open(file_path, "rb") as audio:
                bot.send_audio(message.chat.id, audio, caption=f"🎵 {title}")

            bot.delete_message(message.chat.id, msg.message_id)

        except Exception as e:
            bot.edit_message_text(f"❌ Սխալ: {e}", message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ Չստացվեց ներբեռնել", message.chat.id, msg.message_id)

    cleanup(tmp_dir)


@bot.message_handler(commands=['add'])
def add(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /add երգ")
        return

    uid = message.from_user.id
    playlists.setdefault(uid, []).append(parts[1])

    bot.send_message(message.chat.id, "✅ Ավելացվեց պլեյլիստում")


@bot.message_handler(commands=['playlist'])
def playlist(message):
    uid = message.from_user.id

    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Պլեյլիստը դատարկ է")
        return

    text = "📋 Քո պլեյլիստը՝\n\n"

    for i, song in enumerate(playlists[uid], 1):
        text += f"{i}. 🎵 {song}\n"

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['remove'])
def remove(message):
    parts = message.text.split(maxsplit=1)
    uid = message.from_user.id

    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /remove համար")
        return

    idx = int(parts[1]) - 1

    if uid not in playlists or idx < 0 or idx >= len(playlists[uid]):
        bot.send_message(message.chat.id, "❌ Սխալ համար")
        return

    playlists[uid].pop(idx)

    bot.send_message(message.chat.id, "🗑 Ջնջվեց")


@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.send_message(message.chat.id, "❓ Գրիր /help")


# ──────────────────────────────────────────────

print("✅ Բոտը աշխատում է...")
bot.polling(none_stop=True)
