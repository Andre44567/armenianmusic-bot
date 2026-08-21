import os
import sqlite3
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Այստեղ գրիր ՔՈ Telegram numeric ID-ն
ADMIN_IDS = {ՔՈ_TELEGRAM_ID}

DB = "mafia.db"

ROLES = {
    "mafia": "🔫 Մաֆիա",
    "doctor": "🩺 Բժիշկ",
    "detective": "🔎 Դետեկտիվ",
    "bodyguard": "🛡️ Թիկնապահ",
    "jester": "🤡 Խելագար",
    "hunter": "🎯 Որսորդ",
    "spy": "🕵️ Լրտես",
    "poisoner": "🧪 Թունավորող",
}

players = {}
games = {}


# =========================
# DATABASE
# =========================

def init_db():
    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            diamonds INTEGER DEFAULT 100
        )
    """)

    db.commit()
    db.close()


def register_user(user_id, username):
    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users(user_id, username, diamonds)
        VALUES (?, ?, 100)
    """, (user_id, username))

    cur.execute("""
        UPDATE users
        SET username = ?
        WHERE user_id = ?
    """, (username, user_id))

    db.commit()
    db.close()


def get_diamonds(user_id):
    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        "SELECT diamonds FROM users WHERE user_id = ?",
        (user_id,)
    )

    result = cur.fetchone()
    db.close()

    return result[0] if result else 0


def change_diamonds(user_id, amount):
    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        "UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?",
        (amount, user_id)
    )

    db.commit()
    db.close()


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    register_user(
        user.id,
        user.username or user.first_name
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💎 Իմ ադամանդները",
                callback_data="diamonds"
            )
        ],
        [
            InlineKeyboardButton(
                "🎭 Միանալ Mafia-ին",
                callback_data="join"
            )
        ],
        [
            InlineKeyboardButton(
                "👤 Պրոֆիլ",
                callback_data="profile"
            )
        ]
    ]

    await update.message.reply_text(
        f"Բարի գալուստ, {user.first_name} 👋\n\n"
        "🎭 Բարի գալուստ Mafia աշխարհ։\n"
        "💎 Այստեղ կարող ես խաղալ, հավաքել ադամանդներ "
        "և բացել հատուկ հնարավորություններ։",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# DIAMONDS
# =========================

async def diamonds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = get_diamonds(user.id)

    await update.callback_query.answer()

    await update.callback_query.message.reply_text(
        f"💎 Քո բալանսը՝ **{amount} 💎**",
        parse_mode="Markdown"
    )


# =========================
# PROFILE
# =========================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = get_diamonds(user.id)

    await update.callback_query.answer()

    await update.callback_query.message.reply_text(
        f"👤 **Պրոֆիլ**\n\n"
        f"Username: @{user.username or 'չկա'}\n"
        f"ID: `{user.id}`\n"
        f"💎 Ադամանդներ: **{amount}**",
        parse_mode="Markdown"
    )


# =========================
# JOIN GAME
# =========================

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id in players:
        await update.callback_query.answer(
            "Դու արդեն խաղում ես 😄",
            show_alert=True
        )
        return

    players[user.id] = {
        "name": user.first_name,
        "username": user.username,
        "role": None,
        "alive": True
    }

    await update.callback_query.answer(
        "Դու միացար խաղին 🎭"
    )

    await update.callback_query.message.reply_text(
        f"🎭 {user.first_name} միացավ Mafia-ին։\n"
        f"👥 Խաղացողների քանակը՝ {len(players)}"
    )


# =========================
# ADMIN: GIVE DIAMONDS
# =========================

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Դու ադմին չես։")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Օրինակ՝\n"
            "/give 123456789 500"
        )
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ Սխալ ID կամ քանակ։"
        )
        return

    register_user(user_id, "player")
    change_diamonds(user_id, amount)

    await update.message.reply_text(
        f"✅ Տրվեց {amount} 💎\n"
        f"👤 User ID: {user_id}"
    )


# =========================
# ADMIN: REMOVE DIAMONDS
# =========================

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Դու ադմին չես։")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "/remove USER_ID AMOUNT"
        )
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ Սխալ տվյալ։"
        )
        return

    current = get_diamonds(user_id)

    amount = min(amount, current)

    change_diamonds(user_id, -amount)

    await update.message.reply_text(
        f"✅ Հանվեց {amount} 💎"
    )


# =========================
# START MAFIA
# =========================

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ Միայն ադմինը կարող է սկսել խաղը։"
        )
        return

    if len(players) < 5:
        await update.message.reply_text(
            "❌ Պետք է առնվազն 5 խաղացող։"
        )
        return

    player_ids = list(players.keys())

    random.shuffle(player_ids)

    role_list = []

    role_list += [
        "mafia"
    ] * max(1, len(player_ids) // 4)

    role_list += ["doctor"]
    role_list += ["detective"]
    role_list += ["bodyguard"]

    while len(role_list) < len(player_ids):
        role_list.append(
            random.choice([
                "jester",
                "hunter",
                "spy",
                "poisoner"
            ])
        )

    random.shuffle(role_list)

    for user_id, role in zip(player_ids, role_list):
        players[user_id]["role"] = role
        players[user_id]["alive"] = True

        try:
            await context.bot.send_message(
                user_id,
                f"🎭 Քո դերը՝ **{ROLES[role]}**\n\n"
                "Գաղտնի պահիր քո դերը։ 🤫",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await update.message.reply_text(
        "🌙 **Գիշերը սկսվեց...**\n\n"
        "Բոլորը պատրաստվեք։\n"
        "Յուրաքանչյուր դեր կստանա իր գործողությունը։",
        parse_mode="Markdown"
    )


# =========================
# CALLBACKS
# =========================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "diamonds":
        await diamonds(update, context)

    elif query.data == "profile":
        await profile(update, context)

    elif query.data == "join":
        await join_game(update, context)


# =========================
# MAIN
# =========================

def main():
    init_db()

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN չի գտնվել։ "
            "Railway Variables-ում ավելացրու BOT_TOKEN։"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("startgame", start_game))

    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    print("🤖 Mafia Bot started!")

    app.run_polling()


if __name__ == "__main__":
    main()
