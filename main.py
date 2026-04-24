import os
import re
import urllib.request
import urllib.parse
import telebot
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_server).start()

playlists = {}

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
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "🎵 Բари галуст Khachatryans Ерги Бот!\n\n"
        "🔍 /search ерги анун\n"
        "➕ /add ерги анун\n"
        "📋 /playlist\n"
        "🗑 /remove амар")

@bot.message_handler(commands=['search'])
def search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Грир՝ /search ерги анун")
        return
    query = parts[1]
    bot.send_message(message.chat.id, f"🔍 Воронум ем {query}...")
    link = search_song(query)
    if link:
        bot.send_message(message.chat.id, f"🎵 {query}\n\n🔗 {link}")
    else:
        bot.send_message(message.chat.id, "😔 Чгтнвец։")

@bot.message_handler(commands=['add'])
def add(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Грир՝ /add ерги анун")
        return
    song_name = parts[1]
    uid = message.from_user.id
    if uid not in playlists:
        playlists[uid] = []
    playlists[uid].append(song_name)
    bot.send_message(message.chat.id, f"✅ {song_name} авелацвец!")

@bot.message_handler(commands=['playlist'])
def playlist(message):
    uid = message.from_user.id
    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Плейлистը датарк е։")
        return
    text = "📋 Иmi Плейлистը՝\n\n"
    for i, s in enumerate(playlists[uid], 1):
        text += f"{i}. 🎵 {s}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['remove'])
def remove(message):
    parts = message.text.split(maxsplit=1)
    uid = message.from_user.id
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "⚠️ Грир՝ /remove амар")
        return
    idx = int(parts[1]) - 1
    if uid not in playlists or idx < 0 or idx >= len(playlists[uid]):
        bot.send_message(message.chat.id, "⚠️ Схал амар։")
        return
    removed = playlists[uid].pop(idx)
    bot.send_message(message.chat.id, f"🗑 {removed} херацвец։")

@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.send_message(message.chat.id, "❓ /search ерги анун гри")

print("✅ Ботը гордум е...")
bot.polling(none_stop=True)
