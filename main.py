import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request

import telebot


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չի գտնվել environment variables-ում")

bot = telebot.TeleBot(TOKEN)

playlists = {}


# ──────────────────────────────────────────────
# CORE FUNCTIONS
# ──────────────────────────────────────────────

def search_song(query):
    query_encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={query_encoded}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        html = response.read().decode('utf-8')

        video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"

        return None
    except Exception:
        return None


def download_audio(query):
    """Ներբեռնում է MP3 ֆայլ yt-dlp-ով"""
    link = search_song(query)
    if not link:
        return None, None

    tmp_dir = tempfile.mkdtemp()
    output_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--no-playlist",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
                "-o", output_template,
                "--print", "after_move:filepath",
                link,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        output_path = (
            result.stdout.strip().splitlines()[-1]
            if result.stdout.strip()
            else None
        )

        if output_path and os.path.exists(output_path):
            return output_path, tmp_dir

        for f in os.listdir(tmp_dir):
            if f.endswith(".mp3"):
                return os.path.join(tmp_dir, f), tmp_dir

        return None, tmp_dir

    except subprocess.TimeoutExpired:
        return None, tmp_dir
    except FileNotFoundError:
        return None, tmp_dir


def cleanup(tmp_dir):
    """Ջնջում է ժամանակավոր ֆայլերը"""
    if tmp_dir and os.path.exists(tmp_dir):
        for f in os.listdir(tmp_dir):
            try:
                os.remove(os.path.join(tmp_dir, f))
            except Exception:
                pass
        try:
            os.rmdir(tmp_dir)
        except Exception:
            pass


# ──────────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────────

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


@bot.message_handler(commands=['search'])
def search(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /search երգի անուն")
        return

    query = parts[1]
    bot.send_message(message.chat.id, f"🔍 Որոնում եմ՝ {query}...")

    link = search_song(query)

    if link:
        bot.send_message(message.chat.id, f"🎵 {query}\n\n🔗 {link}")
    else:
        bot.send_message(message.chat.id, "😔 Չգտնվեց։")


@bot.message_handler(commands=['download'])
def download(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /download երգի անուն")
        return

    query = parts[1]

    status_msg = bot.send_message(
        message.chat.id,
        f"⏳ Ներբեռնում եմ՝ {query}...\nՍա կարող է 30-60 վայրկյան տևել։"
    )

    file_path, tmp_dir = download_audio(query)

    if file_path and os.path.exists(file_path):
        try:
            bot.edit_message_text(
                "📤 Ուղարկում եմ...",
                message.chat.id,
                status_msg.message_id
            )

            with open(file_path, "rb") as audio_file:
                bot.send_audio(
                    message.chat.id,
                    audio_file,
                    title=query,
                    caption=f"🎵 {query}",
                )

            bot.delete_message(message.chat.id, status_msg.message_id)

        except Exception as e:
            bot.edit_message_text(
                f"❌ Ուղարկման սխալ: {e}",
                message.chat.id,
                status_msg.message_id
            )
    else:
        bot.edit_message_text(
            "❌ Ներբեռնումը ձախողվեց։\n"
            "• Համոզվիր, որ `yt-dlp` տեղադրված է (pip install yt-dlp)\n"
            "• Կամ հնարավոր է YouTube-ը սահմանափակում է",
            message.chat.id,
            status_msg.message_id,
        )

    cleanup(tmp_dir)


@bot.message_handler(commands=['add'])
def add(message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /add երգի անուն")
        return

    song = parts[1]
    uid = message.from_user.id

    playlists.setdefault(uid, []).append(song)

    bot.send_message(message.chat.id, f"✅ {song} ավելացվեց!")


@bot.message_handler(commands=['playlist'])
def playlist(message):
    uid = message.from_user.id

    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Պլեյլիստը դատարկ է։")
        return

    text = "📋 Իմ պլեյլիստը՝\n\n"

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
        bot.send_message(message.chat.id, "⚠️ Սխալ համար։")
        return

    removed = playlists[uid].pop(idx)

    bot.send_message(message.chat.id, f"🗑 {removed} հեռացվեց։")


@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.send_message(message.chat.id, "❓ Գրիր /help")


# ──────────────────────────────────────────────

print("✅ Բոտը գործում է...")
bot.polling(none_stop=True)
