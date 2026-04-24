import os
import subprocess
import tempfile

import telebot


# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN չի գտնվել")

bot = telebot.TeleBot(TOKEN)

playlists = {}


# ──────────────────────────────────────────────
# CORE FUNCTIONS
# ──────────────────────────────────────────────

def search_song(query):
    """գտնում է առաջին YouTube result-ը yt-dlp-ով"""
    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "yt_dlp",
                f"ytsearch1:{query}",
                "--get-id"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        video_id = result.stdout.strip()

        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

        return None
    except Exception:
        return None


def download_audio(query):
    """ներբեռնում է MP3"""
    link = search_song(query)

    if not link:
        return None, None

    tmp_dir = tempfile.mkdtemp()
    output_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")

    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "yt_dlp",
                "--no-playlist",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
                "-o", output_template,
                link,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )

        # փնտրում ենք mp3 ֆայլը
        for f in os.listdir(tmp_dir):
            if f.endswith(".mp3"):
                return os.path.join(tmp_dir, f), tmp_dir

        return None, tmp_dir

    except Exception:
        return None, tmp_dir


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
# HANDLERS
# ──────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search                            
