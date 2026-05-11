import os
import logging
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

users: set = set()

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)
    await update.message.reply_text(
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "Ուղարկիր հղում՝\n"
        "• YouTube → MP3 🎶\n"
        "• TikTok / Instagram → MP4 📹"
    )

async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Դու admin չես։")
        return
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Օգտագործում՝ /broadcast <տեքստ>")
        return
    ok = fail = 0
    for uid in users:
        try:
            await ctx.bot.send_message(chat_id=uid, text=text)
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"✅ Ուղարկված: {ok} | ❌ Ձախողված: {fail}")

def _download_audio(url):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"/tmp/{info['id']}.mp3"

def _download_video(url):
    opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"/tmp/{info['id']}.{info.get('ext','mp4')}", info.get("title", "")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("Ուղարկիր YouTube, TikTok կամ Instagram հղում։")
        return

    is_yt = any(x in url for x in ("youtube.com", "youtu.be", "music.youtube"))
    is_tt = "tiktok.com" in url
    is_ig = "instagram.com" in url

    if is_yt:
        msg = await update.message.reply_text("⏳ YouTube-ից ներբեռնում...")
        try:
            path = await asyncio.to_thread(_download_audio, url)
            await msg.edit_text("📤 Ուղարկում...")
            with open(path, "rb") as f:
                await update.message.reply_audio(f)
            os.remove(path)
            await msg.delete()
        except Exception as e:
            logger.error(e)
            await msg.edit_text("❌ Չհաջողվեց։ Ստուգիր հղումը։")

    elif is_tt or is_ig:
        src = "TikTok" if is_tt else "Instagram"
        msg = await update.message.reply_text(f"⏳ {src}-ից ներբեռնում...")
        try:
            path, title = await asyncio.to_thread(_download_video, url)
            if os.path.getsize(path) > 50 * 1024 * 1024:
                await msg.edit_text("❌ Ֆայլը 50MB-ից մեծ է։")
            else:
                await msg.edit_text("📤 Ուղարկում...")
                with open(path, "rb") as f:
                    await update.message.reply_video(f, caption=title)
                os.remove(path)
                await msg.delete()
        except Exception as e:
            logger.error(e)
            await msg.edit_text("❌ Չհաջողվեց։ Ստուգիր հղումը։")
    else:
        await update.message.reply_text("❌ Միայն YouTube, TikTok, Instagram հղումներ։")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
