import os
import subprocess
import tempfile
import shutil

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


def send_media(chat_id, filepath):
    extension = os.path.splitext(filepath)[1].lower()

    if extension in [".jpg", ".jpeg", ".png", ".webp"]:
        method = "sendPhoto"
        field = "photo"
    elif extension in [".mp4", ".mov", ".mkv", ".webm"]:
        method = "sendVideo"
        field = "video"
    else:
        method = "sendDocument"
        field = "document"

    with open(filepath, "rb") as media:
        requests.post(
            f"{TELEGRAM_API}/{method}",
            data={
                "chat_id": chat_id
            },
            files={
                field: media
            },
            timeout=120
        )


def download_instagram(url):
    temp_dir = tempfile.mkdtemp()

    output = os.path.join(
    temp_dir,
    "%(playlist_index)s_%(id)s.%(ext)s"
    )

    command = [
        "yt-dlp",
        "--no-warnings",
        "--restrict-filenames",
        "-o",
        output,
        url
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180
    )

    if result.returncode != 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(result.stderr[-1000:])

    files = []

    for filename in os.listdir(temp_dir):
        path = os.path.join(temp_dir, filename)

        if os.path.isfile(path):
            files.append(path)

    if not files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception("No media downloaded.")

    return temp_dir, files


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
            "Send a public Instagram Reel, Video, Photo or Carousel link. 🚀"
        )
        return "OK"

    if "instagram.com/" not in text:
        send_message(
            chat_id,
            "❌ Please send a valid public Instagram URL."
        )
        return "OK"

    send_message(
        chat_id,
        "⏳ Downloading...\nPlease wait."
    )

    temp_dir = None

    try:
        temp_dir, files = download_instagram(text)

        # Send each media file separately
        for filepath in files:
            send_media(chat_id, filepath)

        send_message(
            chat_id,
            f"✅ Done! {len(files)} media file(s) sent."
        )

    except subprocess.TimeoutExpired:
        send_message(
            chat_id,
            "⏱️ Download took too long. Try a smaller public post."
        )

    except Exception as error:
        print("DOWNLOAD ERROR:", error)

        send_message(
            chat_id,
            "❌ Download failed.\n\n"
            "Make sure the Instagram post is public "
            "and the URL is valid."
        )

    finally:
        if temp_dir:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    return "OK"
