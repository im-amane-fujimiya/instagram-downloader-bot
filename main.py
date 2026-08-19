import os
import subprocess
import tempfile

import requests
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text
        },
        timeout=30
    )


def send_video(chat_id, filepath):
    with open(filepath, "rb") as video:
        requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={
                "chat_id": chat_id
            },
            files={
                "video": video
            },
            timeout=120
        )


def download_instagram(url):
    temp_dir = tempfile.mkdtemp()
    output = os.path.join(temp_dir, "video.%(ext)s")

    command = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "best[ext=mp4]/best",
        "-o",
        output,
        url
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise Exception(result.stderr[-1000:])

    files = os.listdir(temp_dir)

    if not files:
        raise Exception("No video downloaded.")

    return os.path.join(temp_dir, files[0])


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
    text = message.get("text", "").strip()

    if not chat:
        return "OK"

    chat_id = chat["id"]

    if text == "/start":
        send_message(
            chat_id,
            "👋 Instagram Downloader Bot\n\n"
            "Public Instagram Reel ka link bhejo. 🚀"
        )
        return "OK"

    if "instagram.com/" not in text:
        send_message(
            chat_id,
            "❌ Instagram ka valid public URL bhejo."
        )
        return "OK"

    send_message(
        chat_id,
        "⏳ Downloading... Please wait."
    )

    try:
        filepath = download_instagram(text)

        send_video(
            chat_id,
            filepath
        )

    except Exception:
        send_message(
            chat_id,
            "❌ Download failed.\n\n"
            "Link public hona chahiye aur Instagram URL supported hona chahiye."
        )

    return "OK"
