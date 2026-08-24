from flask import Flask, request
import os, requests, re

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

# --- Yaha tera sara function ayega ---
def download_insta(link):
    try:
        # Simple downloader logic - tu apna API yaha daal sakta hai
        return link
    except: return None

@app.route('/', methods=['GET', 'POST'])
@app.route('/api', methods=['GET', 'POST'])
@app.route('/api/index', methods=['GET', 'POST'])
def bot():
    if request.method == "GET":
        return "MONSTER V3 LIVE 🔥 | Insta Downloader Ready", 200

    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok", 200
        
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")

        if "/start" in text:
            requests.post(f"{TELEGRAM_API}/sendPhoto", json={
                "chat_id": chat_id,
                "photo": START_PHOTO,
                "caption": "🔥 <b>MONSTER DOWNLOADER ON!</b>\n\nInsta link bhej, direct video dunga!",
                "parse_mode": "HTML"
            })
        elif "instagram.com" in text:
            requests.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"📥 Downloading... \n{ text }"
            })
            # Yaha download logic add hoga
            # requests.post(f"{TELEGRAM_API}/sendVideo", ...)

    except Exception as e:
        print(e)
    return "ok", 200
