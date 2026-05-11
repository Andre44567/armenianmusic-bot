import os
import logging
import asyncio
import yt_dlp

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

users = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)

    text = (
        "🎵 Բարի գալուստ\n\n"
        "📥 YouTube → MP3\n"
        "📥 TikTok / Instagram → MP4\n\n"
        "📎 Ուղարկիր հղումը"
    )

    await update.message.reply_text(text)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Դու ադմին չես")
        return

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text(
            "Օգտագործում:\n/broadcast text"
        )
        return

    ok = 0
    fail = 0

    for uid in users:
        try:
            await context.bot.send_message(uid, text)
            ok += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"✅ Ուղարկվեց {ok}\n❌ Սխալ {fail}"
    )


def download_audio(url):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        file_path = f"/tmp/{info['id']}.mp3"
        title = info.get("title", "audio")

        return file_path, title


def download_video(url):
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        ext = info.get("ext", "mp4")
        file_path = f"/tmp/{info['id']}.{ext}"
        title = info.get("title", "video")

        return file_path, title


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)

    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text(
            "❌ Ուղարկիր ճիշտ հղում"
        )
        return

    is_youtube = (
        "youtube.com" in url
        or "youtu.be" in url
    )

    is_tiktok = "tiktok.com" in url
    is_instagram = "instagram.com" in url

    status = await update.message.reply_text(
        "⏳ Բեռնվում է..."
    )

    try:
        if is_youtube:
            path, title = await asyncio.to_thread(
                download_audio,
                url
            )

            with open(path, "rb") as audio:
                await update.message.reply_audio(
                    audio=audio,
                    title=title
                )

            os.remove(path)

        elif is_tiktok or is_instagram:
            path, title = await asyncio.to_thread(
                download_video,
                url
            )

            with open(path, "rb") as video:
                await update.message.reply_video(
                    video=video,
                    caption=title
                )

            os.remove(path)

        else:
            await status.edit_text(
                "❌ Միայն YouTube / TikTok / Instagram"
            )
            return

        await status.delete()

    except Exception as e:
        logger.error(e)

        await status.edit_text(
            f"❌ Սխալ:\n{str(e)}"
        )


def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN not found")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()
