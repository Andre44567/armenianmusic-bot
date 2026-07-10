import os
import re
import logging
import threading
import subprocess
import tempfile

# Ինքնաշխատ թարմացնում ենք yt-dlp-ը սերվերի վրա (հաջորդ գործարկման ժամանակ կկիրառվի)
try:
    subprocess.run(["pip", "install", "--upgrade", "yt-dlp", "--quiet"], check=False)
except Exception:
    pass

import telebot
from telebot import types
import yt_dlp

# ---------------------- ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ----------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
START_PHOTO_URL = os.environ.get("START_PHOTO_URL", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable-ը սահմանված չէ!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

users = set()
pending_urls = {}  # message_id -> url (YouTube ձևաչափի ընտրության համար)

DOWNLOAD_DIR = tempfile.gettempdir()

YOUTUBE_RE = re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE)
INSTAGRAM_RE = re.compile(r"instagram\.com", re.IGNORECASE)
THREADS_RE = re.compile(r"threads\.net", re.IGNORECASE)


def is_admin(user_id):
    return user_id == ADMIN_ID


def detect_platform(url):
    if YOUTUBE_RE.search(url):
        return "youtube"
    if INSTAGRAM_RE.search(url):
        return "instagram"
    if THREADS_RE.search(url):
        return "threads"
    return None


# ---------------------- ՆԵՐԲԵՌՆՄԱՆ ՖՈՒՆԿՑԻԱ ----------------------

def download_and_send(chat_id, url, audio_only=False):
    bot.send_chat_action(chat_id, "typing")

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "format": "bestaudio/best" if audio_only else "best",
    }
    if audio_only:
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    filename = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if audio_only:
                filename = os.path.splitext(filename)[0] + ".mp3"

        ext = os.path.splitext(filename)[1].lower()
        title = (info.get("title") or "Ֆայլ")[:60]

        with open(filename, "rb") as f:
            if audio_only or ext == ".mp3":
                bot.send_audio(chat_id, f, title=title)
            elif ext in (".jpg", ".jpeg", ".png", ".webp"):
                bot.send_photo(chat_id, f)
            else:
                bot.send_video(chat_id, f, caption=title)

    except Exception as e:
        logger.exception("Download failed for %s", url)
        bot.send_message(
            chat_id,
            "❌ Ներբեռնումը ձախողվեց։ Հնարավոր է՝ հղումը սխալ է, "
            "էջը փակ/պաշտպանված է, կամ պլատֆորմը ժամանակավորապես արգելափակել է հասանելիությունը։"
        )
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError:
                pass


# ---------------------- ՀՐԱՄԱՆՆԵՐ ----------------------

@bot.message_handler(commands=["start"])
def start_handler(message):
    users.add(message.chat.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📖 Ինչպես օգտագործել", callback_data="help"))

    text = (
        "👋 Բարի գալուստ!\n\n"
        "Ուղարկիր ինձ հղում YouTube, Instagram կամ Threads-ից, "
        "և ես կներբեռնեմ երգը, վիդեոն կամ նկարը քեզ համար։"
    )

    if START_PHOTO_URL:
        bot.send_photo(message.chat.id, START_PHOTO_URL, caption=text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_callback(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "📌 Պարզապես ուղարկիր հղումը (YouTube/Instagram/Threads) և ես կուղարկեմ ֆայլը։\n\n"
        "Ադմինիստրատորի համար՝\n"
        "/broadcast <տեքստ> — հաղորդագրություն կուղարկվի բոլոր օգտատերերին։"
    )


@bot.message_handler(commands=["broadcast"])
def broadcast_handler(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Այս հրամանը հասանելի է միայն ադմինիստրատորին։")
        return

    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.reply_to(message, "✏️ Օգտագործում՝ /broadcast Ձեր հաղորդագրությունը")
        return

    sent, failed = 0, 0
    for chat_id in list(users):
        try:
            bot.send_message(chat_id, text)
            sent += 1
        except Exception:
            failed += 1

    bot.reply_to(message, f"✅ Ուղարկվեց {sent} օգտատերի։\n❌ Չհաջողվեց՝ {failed}")


# ---------------------- ՀՂՈՒՄՆԵՐԻ ՄՇԱԿՈՒՄ ----------------------

@bot.message_handler(func=lambda m: m.content_type == "text" and m.text.strip().startswith("http"))
def link_handler(message):
    users.add(message.chat.id)
    url = message.text.strip()
    platform = detect_platform(url)

    if platform is None:
        bot.reply_to(message, "❌ Այս հղումը չեմ ճանաչում։ Ուղարկիր YouTube, Instagram կամ Threads հղում։")
        return

    if platform == "youtube":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🎵 Երգ (MP3)", callback_data="yt_audio"),
            types.InlineKeyboardButton("🎬 Վիդեո", callback_data="yt_video"),
        )
        sent_msg = bot.reply_to(message, "Ընտրիր ձևաչափը 👇", reply_markup=markup)
        pending_urls[sent_msg.message_id] = url
    else:
        bot.reply_to(message, "⏳ Ներբեռնում եմ, մի պահ...")
        threading.Thread(target=download_and_send, args=(message.chat.id, url, False)).start()


@bot.callback_query_handler(func=lambda call: call.data in ("yt_audio", "yt_video"))
def yt_choice_callback(call):
    bot.answer_callback_query(call.id)
    url = pending_urls.pop(call.message.message_id, None)

    if not url:
        bot.send_message(call.message.chat.id, "❌ Հղումի ժամկետը լրացել է, կրկին ուղարկիր հղումը։")
        return

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    audio_only = call.data == "yt_audio"
    bot.send_message(call.message.chat.id, "⏳ Ներբեռնում եմ, մի պահ...")
    threading.Thread(target=download_and_send, args=(call.message.chat.id, url, audio_only)).start()


# ---------------------- ԳՈՐԾԱՐԿՈՒՄ ----------------------

if __name__ == "__main__":
    logger.info("Բոտը գործարկվեց...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
