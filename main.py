import telebot
import os
import re
import urllib.request
import urllib.parse
from flask import Flask
from threading import Thread

# Keep-alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_server).start()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

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

def download_song(query):
    try:
        import subprocess
        query_encoded = urllib.parse.quote(query)
        search_url = f"ytsearch1:{query}"
        result = subprocess.run(
            ['yt-dlp', '-x', '--audio-format', 'mp3',
             '--audio-quality', '0',
             '-o', '/tmp/%(title)s.%(ext)s',
             '--print', 'after_move:filepath',
             search_url],
            capture_output=True, text=True, timeout=60
        )
        filepath = result.stdout.strip().split('\n')[-1]
        if filepath and os.path.exists(filepath):
            return filepath
        return None
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "🎵 Բարի գալուստ Khachatryans Երգի Բոտ!\n\n"
        "🔍 /search երգի անուն — YouTube հղում\n"
        "🎧 /song երգի անուն — ուղղակի ուղարկի երգը\n"
        "➕ /add երգի անուն\n"
        "📋 /playlist\n"
        "🗑 /remove համար")

@bot.message_handler(commands=['search'])
def search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /search երգի անուն")
        return
    query = parts[1]
    bot.send_message(message.chat.id, f"🔍 Որոնում եմ {query}...")
    link = search_song(query)
    if link:
        bot.send_message(message.chat.id, f"🎵 {query}\n\n🔗 {link}")
    else:
        bot.send_message(message.chat.id, "😔 Չգտնվեց։")

@bot.message_handler(commands=['song'])
def song(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /song երգի անուն")
        return
    query = parts[1]
    msg = bot.send_message(message.chat.id, f"⏳ Բեռնում եմ {query}... սպասիր")
    filepath = download_song(query)
    if filepath:
        with open(filepath, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=query)
        os.remove(filepath)
        bot.delete_message(message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("😔 Չհաջողվեց բեռնել։ Փորձիր /search",
                              message.chat.id, msg.message_id)

@bot.message_handler(commands=['add'])
def add(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /add երգի անուն")
        return
    song_name = parts[1]
    uid = message.from_user.id
    if uid not in playlists:
        playlists[uid] = []
    playlists[uid].append(song_name)
    bot.send_message(message.chat.id, f"✅ {song_name} ավելացվեց!")

@bot.message_handler(commands=['playlist'])
def playlist(message):
    uid = message.from_user.id
    if uid not in playlists or not playlists[uid]:
        bot.send_message(message.chat.id, "📋 Պլейлիստը դատարկ է։")
        return
    text = "📋 Իմ Պլейлիստը՝\n\n"
    for i, s in enumerate(playlists[uid], 1):
        text += f"{i}. 🎵 {s}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['remove'])
def remove(message):
    parts = message.text.split(maxsplit=1)
    uid = message.from_user.id
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "⚠️ Գրիր՝ /remove համар")
        return
    idx = int(parts[1]) - 1
    if uid not in playlists or idx < 0 or idx >= len(playlists[uid]):
        bot.send_message(message.chat.id, "⚠️ Սխալ համар։")
        return
    removed = playlists[uid].pop(idx)
    bot.send_message(message.chat.id, f"🗑 {removed} հեռացվեց։")

@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.send_message(message.chat.id, "❓ Օգտագործիր /song կամ /search")

print("✅ Բոտը գործում է...")
keep_alive()
bot.polling(none_stop=True)
