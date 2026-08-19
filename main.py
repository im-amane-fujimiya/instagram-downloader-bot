import os
import subprocess
import tempfile
import shutil

import requests
from flask import Flask, request

from extractor import extract_instagram_media, cleanup_media


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
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            data={
                "chat_id": chat_id
            },
            files={
                field: media
            },
            timeout=120
        )

    response.raise_for_status()


def download_with_ytdlp(url):
    """
    Existing working Reel/Video downloader.
    """

    temp_dir = tempfile.mkdtemp()

    output = os.path.join(
        temp_dir,
        "%(playlist_index)s_%(id)s.%(ext)s"
    )

    command = [
        "yt-dlp",
        "--no-warnings",
        "--restrict-filenames",
        "--no-playlist",
        "-o",
        output,
        url
    ]

    print(
        "YTDLP:",
        " ".join(command)
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180
    )

    print(
        "YTDLP RETURN CODE:",
        result.returncode
    )

    print(
        "YTDLP STDERR:",
        result.stderr[-2000:]
    )

    if result.returncode != 0:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise Exception(
            result.stderr[-1000:]
        )

    files = []

    for filename in os.listdir(temp_dir):
        path = os.path.join(
            temp_dir,
            filename
        )

        if os.path.isfile(path):
            files.append(path)

    if not files:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise Exception(
            "yt-dlp finished but no media file was created."
        )

    return temp_dir, files


def is_instagram_url(url):
    return (
        "instagram.com/" in url.lower()
    )


@app.get("/")
def home():
    return "Instagram Downloader Bot is running!"


@app.post("/webhook")
def webhook():

    data = request.get_json(
        silent=True
    ) or {}

    message = data.get("message")

    if not message:
        return "OK"

    chat = message.get("chat")
    text = message.get(
        "text",
        ""
    ).strip()

    if not chat:
        return "OK"

    chat_id = chat["id"]

    # START
    if text == "/start":

        send_message(
            chat_id,
            "👋 Instagram Downloader Bot\n\n"
            "Send a public Instagram Reel, Video, "
            "Photo or Carousel link. 🚀"
        )

        return "OK"

    # URL CHECK
    if not is_instagram_url(text):

        send_message(
            chat_id,
            "❌ Please send a valid public "
            "Instagram URL."
        )

        return "OK"

    send_message(
        chat_id,
        "⏳ Downloading...\n"
        "Please wait."
    )

    ytdlp_dir = None
    extractor_dir = None

    try:

        # ------------------------------------------------
        # FIRST: Try the existing yt-dlp downloader.
        # This keeps your working Reel functionality.
        # ------------------------------------------------

        try:

            ytdlp_dir, files = (
                download_with_ytdlp(text)
            )

            print(
                "yt-dlp succeeded:",
                files
            )

        except Exception as ytdlp_error:

            print(
                "yt-dlp failed:",
                repr(ytdlp_error)
            )

            # --------------------------------------------
            # FALLBACK:
            # Use parth-dl for photos/carousels/posts.
            # --------------------------------------------

            send_message(
                chat_id,
                "🔄 Trying alternate Instagram "
                "media extractor..."
            )

            extractor_dir, files = (
                extract_instagram_media(text)
            )

        # ------------------------------------------------
        # SEND MEDIA
        # ------------------------------------------------

        sent = 0

        for filepath in files:

            try:

                send_media(
                    chat_id,
                    filepath
                )

                sent += 1

            except Exception as send_error:

                print(
                    "TELEGRAM SEND ERROR:",
                    repr(send_error)
                )

        if sent == 0:

            raise Exception(
                "No media could be sent to Telegram."
            )

        send_message(
            chat_id,
            f"✅ Done!\n"
            f"{sent} media file(s) sent."
        )

    except subprocess.TimeoutExpired:

        send_message(
            chat_id,
            "⏱️ Download timed out.\n\n"
            "Try a smaller public Instagram post."
        )

    except Exception as error:

        error_text = str(error)

        print(
            "DOWNLOAD ERROR:",
            repr(error_text)
        )

        send_message(
            chat_id,
            "❌ Download failed.\n\n"
            "Error:\n"
            + error_text[-1000:]
        )

    finally:

        if ytdlp_dir:

            shutil.rmtree(
                ytdlp_dir,
                ignore_errors=True
            )

        if extractor_dir:

            cleanup_media(
                extractor_dir
            )

    return "OK"
