import os
import logging
import yt_dlp
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "123456789"))  # փոխիր կամ env-ից դիր

users: set[int] = set()

# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.add(uid)
    await update.message.reply_text(
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "Ուղարկիր YouTube, TikTok կամ Instagram հղում՝\n"
        "• YouTube → ստանաս MP3 երաժշտություն 🎶\n"
        "• TikTok / Instagram → ստանաս MP4 վիդեո 📹\n\n"
        "Պարզապես ուղարկիր հղումը ⬇️"
    )

# ──────────────────────────────────────────────
# /broadcast  (only admin)
# ──────────────────────────────────────────────
async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("❌ Դու admin չես։")
        return

    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Օգտագործում՝ /broadcast <տեքստ>")
        return

    ok = fail = 0
    for user_id in users:
        try:
            await ctx.bot.send_message(chat_id=user_id, text=text)
            ok += 1
        except Exception:
            fail += 1

    await update.message.reply_text(f"✅ Ուղարկված: {ok} | ❌ Ձախողված: {fail}")

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def is_youtube(url: str) -> bool:
    return any(x in url for x in ("youtube.com", "youtu.be", "music.youtube"))

def is_tiktok(url: str) -> bool:
    return "tiktok.com" in url

def is_instagram(url: str) -> bool:
    return "instagram.com" in url

# ──────────────────────────────────────────────
# Download YouTube → MP3
# ──────────────────────────────────────────────
async def download_youtube_audio(url: str) -> str | None:
    opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return f"/tmp/{info['id']}.mp3"
    except Exception as e:
        logger.error("YouTube audio error: %s", e)
        return None

# ──────────────────────────────────────────────
# Download TikTok / Instagram → MP4
# ──────────────────────────────────────────────
async def download_video(url: str) -> tuple[str | None, str | None]:
    opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")
            path = f"/tmp/{info['id']}.{ext}"
            title = info.get("title", "Video")
            return path, title
    except Exception as e:
        logger.error("Video download error: %s", e)
        return None, None

# ──────────────────────────────────────────────
# Message handler — link detector
# ──────────────────────────────────────────────
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.add(uid)

    text = update.message.text.strip()

    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text("Ուղարկիր YouTube, TikTok կամ Instagram հղում։")
        return

    # ── YouTube ──────────────────────────────
    if is_youtube(text):
        msg = await update.message.reply_text("⏳ YouTube-ից ներբեռնում... սպասիր")
        path = await asyncio.to_thread(lambda: _sync_download_youtube(text))
        if path and os.path.exists(path):
            await msg.edit_text("📤 Ուղարկում...")
            with open(path, "rb") as f:
                await update.message.reply_audio(f)
            os.remove(path)
            await msg.delete()
        else:
            await msg.edit_text("❌ Չհաջողվեց ներբեռնել։ Ստուգիր հղումը։")

    # ── TikTok / Instagram ───────────────────
    elif is_tiktok(text) or is_instagram(text):
        source = "TikTok" if is_tiktok(text) else "Instagram"
        msg = await update.message.reply_text(f"⏳ {source}-ից ներբեռնում... սպասիր")
        path, title = await asyncio.to_thread(lambda: _sync_download_video(text))
        if path and os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > 50:
                await msg.edit_text("❌ Ֆայլը 50 MB-ից մեծ է, Telegram-ը չի ընդունում։")
            else:
                await msg.edit_text("📤 Ուղարկում...")
                with open(path, "rb") as f:
                    await update.message.reply_video(f, caption=title or source)
                os.remove(path)
                await msg.delete()
        else:
            await msg.edit_text("❌ Չհաջողվեց ներբեռնել։ Ստուգիր հղումը։")

    else:
        await update.message.reply_text("❌ Աջակցվում են միայն YouTube, TikTok, Instagram հղումներ։")


def _sync_download_youtube(url: str) -> str | None:
    opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return f"/tmp/{info['id']}.mp3"
    except Exception as e:
        logger.error("YT sync error: %s", e)
        return None


def _sync_download_video(url: str) -> tuple[str | None, str | None]:
    opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")
            return f"/tmp/{info['id']}.{ext}", info.get("title")
    except Exception as e:
        logger.error("Video sync error: %s", e)
        return None, None


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started…")
    app.run_polling()


if __name__ == "__main__":
    main()
