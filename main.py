import os
import requests
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]

app = Flask(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text
        },
        timeout=20
    )


@app.get("/")
def home():
    return "Instagram Downloader Bot is running!"


@app.post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}

    message = data.get("message")

    if not message:
        return "OK"

    chat = message.get("chat")
    text = message.get("text", "")

    if not chat:
        return "OK"

    chat_id = chat["id"]

    if text == "/start":
        send_message(
            chat_id,
            "👋 Hello!\n\n"
            "Instagram Downloader Bot is online! 🚀\n\n"
            "Instagram ka public Reel/Post link bhejo."
        )

    elif text.startswith("http"):
        send_message(
            chat_id,
            "🔗 Link received!\n\n"
            "Downloader engine abhi setup ho raha hai. 🚀"
        )

    else:
        send_message(
            chat_id,
            "📸 Instagram ka public link bhejo."
        )

    return "OK"
