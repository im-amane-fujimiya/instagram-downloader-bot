from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

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
        if not data or "message" not in data:
            return "ok", 200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        if "/start" in text:
            requests.post(f"{TELEGRAM_API}/sendPhoto", json={
                "chat_id": chat_id,
                "photo": START_PHOTO,
                "caption": "🎬 <b>Bot ON! Link bhej!</b>",
                "parse_mode": "HTML"
            }, timeout=10)
    except Exception as e:
        print(e)
    return "ok", 200
