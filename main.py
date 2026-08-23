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

def sb_add_user(chat_id, username=""):
    try:
        if not SUPABASE_URL: return
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
        requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=headers, json={"chat_id": chat_id, "username": username}, timeout=5)
    except: pass

@app.route('/')
@app.route('/api')
@app.route('/api/')
@app.route('/api/index')
@app.route('/api/index/')
def home():
    return "MONSTER V3 LIVE 🔥", 200

@app.route('/', methods=['POST'])
@app.route('/api', methods=['POST'])
@app.route('/api/', methods=['POST'])
@app.route('/api/index', methods=['POST'])
@app.route('/api/index/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data: return "ok", 200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        username = data["message"]["from"].get("username","")
        sb_add_user(chat_id, username)
        
        if "/start" in text:
            kb = {"inline_keyboard": [[{"text": "📥 Download", "url": "https://t.me/"}]]}
            requests.post(f"{TELEGRAM_API}/sendPhoto", json={
                "chat_id": chat_id, 
                "photo": START_PHOTO, 
                "caption": "🎬 <b>Bot ON! Link bhej!</b>", 
                "parse_mode": "HTML",
                "reply_markup": kb
            }, timeout=10)
    except Exception as e:
        print(f"Error: {e}")
    return "ok", 200
