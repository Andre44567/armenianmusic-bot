import os
import sqlite3
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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

# Այստեղ տեղադրեք ձեր Telegram numeric ID-ն
ADMIN_IDS = {123456789}

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


def get_top_players():
    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        "SELECT username, diamonds FROM users ORDER BY diamonds DESC LIMIT 5"
    )

    result = cur.fetchall()
    db.close()
    return result


# =========================
# MAIN MENU KEYBOARD
# =========================

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🎭 Միանալ Mafia-ին"), KeyboardButton("🚪 Դուրս գալ")],
        [KeyboardButton("💎 Իմ ադամանդները"), KeyboardButton("👤 Պրոֆիլ")],
        [KeyboardButton("🏆 Թոփ 5"), KeyboardButton("📜 Կանոններ")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    register_user(
        user.id,
        user.username or user.first_name
    )

    inline_keyboard = [
        [InlineKeyboardButton("🎭 Միանալ Mafia-ին", callback_data="join")],
        [InlineKeyboardButton("💎 Իմ ադամանդները", callback_data="diamonds"), InlineKeyboardButton("👤 Պրոֆիլ", callback_data="profile")]
    ]

    await update.message.reply_text(
        f"Բարի գալուստ, {user.first_name} 👋\n\n"
        "🎭 Բարի գալուստ Mafia աշխարհ։\n"
        "💎 Այստեղ կարող ես խաղալ, հավաքել ադամանդներ "
        "և բացել հատուկ հնարավորություններ։\n\n"
        "👇 Օգտագործիր ներքևի կոճակները արագ նավիգացիայի համար։",
        reply_markup=get_main_keyboard()
    )


async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📜 **Mafia Խաղի Կանոնները**\n\n"
        "1. Խաղին մասնակցում է առնվազն 5 խաղացող։\n"
        "2. Գիշերը յուրաքանչյուր հատուկ դեր կատարում է իր գործողությունը (Մաֆիան կրակում է, Բժիշկը բուժում է և այլն)։\n"
        "3. Ցերեկը բոլոր խաղացողները քննարկում են և քվեարկում կասկածյալի օգտին։\n\n"
        "🎭 **Դերեր:**\n"
        "• 🔫 Մաֆիա - Սպանում է քաղաքացիներին\n"
        "• 🩺 Բժիշկ - Փրկում է 1 խաղացողի\n"
        "• 🔎 Դետեկտիվ - Ստուգում է խաղացողի դերը\n"
        "• 🛡️ Թիկնապահ - Պաշտպանում է հարձակումից\n"
        "• 🤡 Խելագար - Հաղթում է, եթե իրեն ցերեկով քվեարկեն"
    )
    await update.message.reply_text(rules_text, parse_mode="Markdown")


async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_data = get_top_players()
    text = "🏆 **Ամենաշատ ադամանդ ունեցող Top 5 խաղացողները:**\n\n"
    for idx, (username, diamonds) in enumerate(top_data, 1):
        text += f"{idx}. @{username or 'անանուն'} — **{diamonds}** 💎\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in players:
        del players[user.id]
        await update.message.reply_text("🚪 Դուք դուրս եկաք խաղի սպասասրահից։")
    else:
        await update.message.reply_text("❌ Դուք խաղի մեջ չեք։")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ **Հասանելի հրամաններ:**\n\n"
        "/start — Սկսել բոտը\n"
        "/menu — Բացել հիմնական կոճակները\n"
        "/leave — Դուրս գալ խաղից\n"
        "/top — Ադամանդների Top 5\n"
        "/rules — Խաղի կանոնները\n"
        "/help — Այս ցուցակը\n\n"
        "👑 **Ադմիններին:**\n"
        "/startgame — Սկսել խաղը\n"
        "/give ID AMOUNT — Ադամանդ տալ\n"
        "/remove ID AMOUNT — Ադամանդ հանել"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# =========================
# TEXT MESSAGES HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    if text == "🎭 Միանալ Mafia-ին":
        if user.id in players:
            await update.message.reply_text("Դուք արդեն միացել եք 😄")
        else:
            players[user.id] = {"name": user.first_name, "username": user.username, "role": None, "alive": True}
            await update.message.reply_text(f"🎭 {user.first_name} միացավ Mafia-ին։\n👥 Խաղացողների քանակը՝ {len(players)}")

    elif text == "🚪 Դուրս գալ":
        await leave_game(update, context)

    elif text == "💎 Իմ ադամանդները":
        amount = get_diamonds(user.id)
        await update.message.reply_text(f"💎 Քո բալանսը՝ **{amount} 💎**", parse_mode="Markdown")

    elif text == "👤 Պրոֆիլ":
        amount = get_diamonds(user.id)
        await update.message.reply_text(
            f"👤 **Պրոֆիլ**\n\nUsername: @{user.username or 'չկա'}\nID: `{user.id}`\n💎 Ադամանդներ: **{amount}**",
            parse_mode="Markdown"
        )

    elif text == "🏆 Թոփ 5":
        await top_players(update, context)

    elif text == "📜 Կանոններ":
        await show_rules(update, context)


# =========================
# DIAMONDS & PROFILE (INLINE)
# =========================

async def diamonds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = get_diamonds(user.id)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f"💎 Քո բալանսը՝ **{amount} 💎**", parse_mode="Markdown")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = get_diamonds(user.id)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        f"👤 **Պրոֆիլ**\n\nUsername: @{user.username or 'չկա'}\nID: `{user.id}`\n💎 Ադամանդներ: **{amount}**",
        parse_mode="Markdown"
    )


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in players:
        await update.callback_query.answer("Դու արդեն խաղում ես 😄", show_alert=True)
        return

    players[user.id] = {"name": user.first_name, "username": user.username, "role": None, "alive": True}
    await update.callback_query.answer("Դու միացար խաղին 🎭")
    await update.callback_query.message.reply_text(f"🎭 {user.first_name} միացավ Mafia-ին։\n👥 Խաղացողների քանակը՝ {len(players)}")


# =========================
# ADMIN COMMANDS
# =========================

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Դու ադմին չես։")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Օրինակ՝\n/give 123456789 500")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Սխալ ID կամ քանակ։")
        return

    register_user(user_id, "player")
    change_diamonds(user_id, amount)
    await update.message.reply_text(f"✅ Տրվեց {amount} 💎\n👤 User ID: {user_id}")


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Դու ադմին չես։")
        return

    if len(context.args) != 2:
        await update.message.reply_text("/remove USER_ID AMOUNT")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Սխալ տվյալ։")
        return

    current = get_diamonds(user_id)
    amount = min(amount, current)
    change_diamonds(user_id, -amount)
    await update.message.reply_text(f"✅ Հանվեց {amount} 💎")


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Միայն ադմինը կարող է սկսել խաղը։")
        return

    if len(players) < 5:
        await update.message.reply_text("❌ Պետք է առնվազն 5 խաղացող։")
        return

    player_ids = list(players.keys())
    random.shuffle(player_ids)

    role_list = ["mafia"] * max(1, len(player_ids) // 4)
    role_list += ["doctor", "detective", "bodyguard"]

    while len(role_list) < len(player_ids):
        role_list.append(random.choice(["jester", "hunter", "spy", "poisoner"]))

    random.shuffle(role_list)

    for user_id, role in zip(player_ids, role_list):
        players[user_id]["role"] = role
        players[user_id]["alive"] = True
        try:
            await context.bot.send_message(
                user_id,
                f"🎭 Քո դերը՝ **{ROLES[role]}**\n\nԳաղտնի պահիր քո դերը։ 🤫",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await update.message.reply_text(
        "🌙 **Գիշերը սկսվեց...**\n\nԲոլորը պատրաստվեք։\nՅուրաքանչյուր դեր կստանա իր գործողությունը։",
        parse_mode="Markdown"
    )


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
        raise ValueError("BOT_TOKEN չի գտնվել։ Railway Variables-ում ավելացրու BOT_TOKEN։")

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("leave", leave_game))
    app.add_handler(CommandHandler("top", top_players))
    app.add_handler(CommandHandler("rules", show_rules))
    app.add_handler(CommandHandler("help", help_command))

    # Admin Commands
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("startgame", start_game))

    # Handlers
    app.add_handler(CallbackQueryHandler(callback_handler))
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Mafia Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
