from flask import Flask, request
import os, requests, re

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@Material_01_01"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_PHOTO = "https://files.catbox.moe/3f7j4v.jpg"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def func_get_caption(html):
    try:
        m = re.search(r'"caption":\{"text":"([^"]+)"', html)
        if m: return m.group(1).encode().decode('unicode_escape')[:800]
    except: pass
    return ""

def sb_add_user(chat_id, username=""):
    return

# YE LINE SABSE IMPORTANT HAI - 404 KHATAM KAREGA
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if request.method == "GET":
        return "MONSTER V3 LIVE 🔥", 200
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        if "/start" in text:
            kb = {"inline_keyboard": [[{"text": "📥 Download", "callback_data": "dl"}]]}
            requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": START_PHOTO, "caption": "🎬 <b>Bot ON! Link bhej!</b>", "parse_mode": "HTML", "reply_markup": kb}, timeout=10)
            return "ok",200
    except Exception as e:
        print(e)
    return "ok",200
