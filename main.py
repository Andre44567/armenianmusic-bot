import os
import logging
from collections import defaultdict

import telebot
from telebot import types
from openai import OpenAI

# ---------------------- ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ----------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
START_PHOTO_URL = os.environ.get("START_PHOTO_URL", "")

# Կարող ես փոխել մոդելը (gpt-4o-mini-ն ամենաէժանն ու արագն է)
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "Դու օգտակար, ընկերասեր AI ասիստենտ ես Telegram-ի բոտում։ "
    "Պատասխանիր հայերեն, եթե օգտատերը հայերեն է գրում։ Եղիր հակիրճ և պարզ։"
)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable-ը սահմանված չէ!")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable-ը սահմանված չէ!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

users = set()

# Յուրաքանչյուր օգտատիրոջ խոսակցության պատմությունը հիշում ենք հիշողության մեջ
# (Railway restart-ից հետո մաքրվում է)
conversations = defaultdict(list)
MAX_HISTORY = 10  # քանի հաղորդագրություն ենք պահում համատեքստում


def is_admin(user_id):
    return user_id == ADMIN_ID


def ask_gpt(chat_id, user_text):
    conversations[chat_id].append({"role": "user", "content": user_text})
    # Սահմանափակում ենք պատմության երկարությունը
    conversations[chat_id] = conversations[chat_id][-MAX_HISTORY:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversations[chat_id]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    reply = response.choices[0].message.content
    conversations[chat_id].append({"role": "assistant", "content": reply})
    return reply


# ---------------------- ՀՐԱՄԱՆՆԵՐ ----------------------

@bot.message_handler(commands=["start"])
def start_handler(message):
    users.add(message.chat.id)
    conversations[message.chat.id] = []

    text = (
        "👋 Բարի գալուստ!\n\n"
        "Ես AI ասիստենտ եմ։ Ուղարկիր ինձ ցանկացած հարց կամ հաղորդագրություն, "
        "և ես կպատասխանեմ։\n\n"
        "/new — սկսել նոր զրույց (մոռանալ նախորդ խոսակցությունը)\n"
        "/image [նկարագրություն] — գեներացնել նկար"
    )

    if START_PHOTO_URL:
        bot.send_photo(message.chat.id, START_PHOTO_URL, caption=text)
    else:
        bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["new"])
def new_conversation_handler(message):
    conversations[message.chat.id] = []
    bot.reply_to(message, "🔄 Նոր զրույց սկսվեց։ Նախորդ խոսակցությունը մոռացվեց։")


@bot.message_handler(commands=["image"])
def image_handler(message):
    prompt = message.text.replace("/image", "", 1).strip()
    if not prompt:
        bot.reply_to(message, "✏️ Օգտագործում՝ /image նկարագրություն (օրինակ՝ /image կատու, որ նվագում է կիթառ)")
        return

    bot.send_chat_action(message.chat.id, "upload_photo")
    status_msg = bot.reply_to(message, "🎨 Նկարը գեներացվում է, մի պահ...")

    try:
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        image_url = result.data[0].url
        bot.send_photo(message.chat.id, image_url, caption=f"🎨 {prompt}")
    except Exception as e:
        logger.exception("Image generation failed")
        bot.reply_to(message, "❌ Նկարը չստացվեց գեներացնել։ Փորձիր այլ նկարագրությամբ կամ մի փոքր ուշ։")
    finally:
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception:
            pass


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


# ---------------------- ՀԱՐՑ-ՊԱՏԱՍԽԱՆ ----------------------

@bot.message_handler(func=lambda m: m.content_type == "text")
def chat_handler(message):
    users.add(message.chat.id)
    bot.send_chat_action(message.chat.id, "typing")

    try:
        reply = ask_gpt(message.chat.id, message.text)
        bot.reply_to(message, reply)
    except Exception as e:
        logger.exception("GPT request failed")
        bot.reply_to(message, "❌ Ինչ-որ բան սխալ գնաց AI-ի հետ կապվելիս։ Փորձիր նորից մի փոքր ուշ։")


# ---------------------- ԳՈՐԾԱՐԿՈՒՄ ----------------------

if __name__ == "__main__":
    logger.info("AI բոտը գործարկվեց...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
