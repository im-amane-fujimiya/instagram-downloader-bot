from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.route("/", methods=["GET"])
def home():
    return "BOT OK"

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": "✅ 500 Fix ho gaya! Bot zinda hai 🔥"}, timeout=10)
    except Exception as e:
        print(e)
    return "ok", 200
