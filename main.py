import os
import re
import asyncio
import tempfile
import shutil
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import instaloader

# ---- Config ----
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("7304274135", "0"))
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL", "")
DB_FILE = "users.json"

# ---- Database ----

def load_users() -> set:
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r") as f:
        return set(json.load(f))

def save_user(user_id: int):
    users = load_users()
    users.add(user_id)
    with open(DB_FILE, "w") as f:
        json.dump(list(users), f)

def get_all_users() -> list:
    return list(load_users())

# ---- Helpers ----

user_state = {}

def detect_platform(url: str) -> str:
    if re.search(r"instagram\.com", url):
        return "instagram"
    elif re.search(r"tiktok\.com", url):
        return "tiktok"
    elif re.search(r"pinterest\.(com|ca|co\.uk|fr|de|es|it|ru|jp)|pin\.it", url):
        return "pinterest"
    return "unknown"

def is_url(text: str) -> bool:
    return bool(re.search(r"https?://", text))

# ---- Download ----

def _sync_instagram(url: str, tmpdir: str) -> list:
    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        dirname_pattern=tmpdir,
        filename_pattern="{shortcode}",
        quiet=True,
    )
    shortcode_match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    if not shortcode_match:
        raise ValueError("Instagram URL-ը ճիշտ չէ")
    shortcode = shortcode_match.group(1)
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target=tmpdir)
    files = []
    for f in os.listdir(tmpdir):
        full = os.path.join(tmpdir, f)
        if f.endswith((".jpg", ".jpeg", ".png", ".mp4")):
            files.append(full)
    return files

def _sync_ytdlp(url: str, tmpdir: str) -> list:
    ydl_opts = {
        "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    files = []
    for f in os.listdir(tmpdir):
        full = os.path.join(tmpdir, f)
        if os.path.isfile(full):
            files.append(full)
    return files

# ---- Send media ----

async def send_media(update: Update, files: list, caption: str):
    for f in files:
        ext = f.lower().split(".")[-1]
        try:
            if ext in ("mp4", "mov", "avi", "mkv"):
                with open(f, "rb") as vid:
                    await update.message.reply_video(vid, caption=caption or None, supports_streaming=True)
            elif ext in ("jpg", "jpeg", "png", "webp"):
                with open(f, "rb") as img:
                    await update.message.reply_photo(img, caption=caption or None)
        except Exception:
            with open(f, "rb") as doc:
                await update.message.reply_document(doc, caption=caption or None)

# ---- Handlers ----

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    save_user(user_id)

    welcome_text = (
        "👋 Բարև! Ես մեդիա ներբեռնիչ բոտ եմ 🤖\n\n"
        "📌 Ինչ կարող եմ անել՝\n"
        "📸 Instagram post / reel\n"
        "🎵 TikTok վիդեո\n"
        "📌 Pinterest նկար / վիդեո\n\n"
        "✅ Ուղղակի ուղարկիր հղումը!"
    )

    try:
        if WELCOME_IMAGE_URL:
            await update.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text)
        else:
            await update.message.reply_text(welcome_text)
    except Exception:
        await update.message.reply_text(welcome_text)

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_state and user_state[user_id].get("waiting_caption"):
        url = user_state[user_id]["url"]
        platform = user_state[user_id]["platform"]
        user_state.pop(user_id, None)
        await process_download(update, url, platform, caption="")
    else:
        await update.message.reply_text("⚠️ Նախ ուղարկիր հղում։")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Դու admin չես։")
        return
    users = get_all_users()
    await update.message.reply_text(f"👥 Ընդհանուր օգտատերեր՝ {len(users)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Դու admin չես։")
        return
    if not context.args:
        await update.message.reply_text(
            "⚠️ Օրինակ՝ `/broadcast Բարև բոլորին!`",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    users = get_all_users()
    msg = await update.message.reply_text(f"📤 Ուղարկում եմ {len(users)} հոգու...")

    success = 0
    failed = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await msg.edit_text(
        f"✅ Broadcast ավարտվեց!\n"
        f"📨 Ուղարկվեց՝ {success}\n"
        f"❌ Չուղարկվեց՝ {failed}"
    )

async def broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Դու admin չես։")
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("⚠️ Նկար ուղարկիր caption-ով, հետո reply արա /broadcast_photo հրամանով։")
        return

    photo = update.message.reply_to_message.photo[-1].file_id
    caption = update.message.reply_to_message.caption or ""
    users = get_all_users()
    msg = await update.message.reply_text(f"📤 Ուղարկում եմ նկար {len(users)} հոգու...")

    success = 0
    failed = 0
    for uid in users:
        try:
            await context.bot.send_photo(chat_id=uid, photo=photo, caption=caption)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await msg.edit_text(
        f"✅ Broadcast ավարտվեց!\n"
        f"📨 Ուղարկվեց՝ {success}\n"
        f"❌ Չուղարկվեց՝ {failed}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id in user_state and user_state[user_id].get("waiting_caption"):
        caption = text
        url = user_state[user_id]["url"]
        platform = user_state[user_id]["platform"]
        user_state.pop(user_id, None)
        await process_download(update, url, platform, caption)
        return

    if is_url(text):
        platform = detect_platform(text)
        if platform == "unknown":
            await update.message.reply_text("❌ Ճանաչված չէ։ Instagram / TikTok / Pinterest հղում ուղարկիր։")
            return
        user_state[user_id] = {"url": text, "platform": platform, "waiting_caption": True}
        await update.message.reply_text(
            f"✅ {platform.capitalize()} հղում ստացա!\n\n"
            "✍️ Գրիր caption կամ /skip եթե caption չես ուզում։"
        )
        return

    await update.message.reply_text("🔗 Ուղարկիր հղում Instagram / TikTok / Pinterest-ից։")

async def process_download(update: Update, url: str, platform: str, caption: str):
    msg = await update.message.reply_text(f"⏳ Ներբեռնում եմ {platform.capitalize()}-ից...")
    tmpdir = tempfile.mkdtemp()
    try:
        loop = asyncio.get_event_loop()
        if platform == "instagram":
            files = await loop.run_in_executor(None, lambda: _sync_instagram(url, tmpdir))
        else:
            files = await loop.run_in_executor(None, lambda: _sync_ytdlp(url, tmpdir))

        if not files:
            await msg.edit_text("❌ Ոչինչ չգտնվեց։")
            return

        await msg.edit_text("📤 Ուղարկում եմ...")
        await send_media(update, files, caption)
        await msg.delete()
        await update.message.reply_text("✅ Պատրաստ է! Forward արա ում ուզում ես 🚀")

    except instaloader.exceptions.LoginRequiredException:
        await msg.edit_text("🔒 Այս Instagram հաշիվը private է։")
    except Exception as e:
        await msg.edit_text(f"❌ Սխալ՝ {str(e)[:200]}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ---- Main ----

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("broadcast_photo", broadcast_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
