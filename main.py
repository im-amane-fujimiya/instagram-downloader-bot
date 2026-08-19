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


def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=data,
        timeout=30
    )


def answer_callback(callback_id):
    requests.post(
        f"{TELEGRAM_API}/answerCallbackQuery",
        json={
            "callback_query_id": callback_id
        },
        timeout=30
    )


def send_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🎬 Reels",
                    "callback_data": "reels"
                },
                {
                    "text": "🎥 Videos",
                    "callback_data": "videos"
                }
            ],
            [
                {
                    "text": "🖼️ Photos",
                    "callback_data": "photos"
                },
                {
                    "text": "📚 Carousel",
                    "callback_data": "carousel"
                }
            ],
            [
                {
                    "text": "❓ Help",
                    "callback_data": "help"
                }
            ]
        ]
    }

    send_message(
        chat_id,
        "📥 Instagram Downloader\n\n"
        "Send any public Instagram link and "
        "I'll download the available media for you. 🚀",
        keyboard
    )


def send_help(chat_id):
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📥 Download",
                    "callback_data": "menu"
                }
            ]
        ]
    }

    send_message(
        chat_id,
        "❓ How to use\n\n"
        "1️⃣ Copy a public Instagram link.\n"
        "2️⃣ Send it to this bot.\n"
        "3️⃣ Wait for the download. 🚀\n\n"
        "✅ Reels\n"
        "✅ Videos\n"
        "✅ Photos\n"
        "✅ Carousels\n\n"
        "🔒 Private or login-protected content "
        "isn't supported.",
        keyboard
    )


def send_media(chat_id, filepath):
    extension = os.path.splitext(filepath)[1].lower()

    if extension in [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    ]:
        method = "sendPhoto"
        field = "photo"

    elif extension in [
        ".mp4",
        ".mov",
        ".mkv",
        ".webm"
    ]:
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
    Existing Reel/Video downloader.
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
    return "instagram.com/" in url.lower()


def handle_button(chat_id, callback_id, action):
    answer_callback(callback_id)

    if action == "menu":
        send_menu(chat_id)

    elif action == "help":
        send_help(chat_id)

    elif action == "reels":
        send_message(
            chat_id,
            "🎬 Reels\n\n"
            "Send a public Instagram Reel link."
        )

    elif action == "videos":
        send_message(
            chat_id,
            "🎥 Videos\n\n"
            "Send a public Instagram video post link."
        )

    elif action == "photos":
        send_message(
            chat_id,
            "🖼️ Photos\n\n"
            "Send a public Instagram photo post link."
        )

    elif action == "carousel":
        send_message(
            chat_id,
            "📚 Carousel\n\n"
            "Send a public Instagram carousel link."
        )


@app.get("/")
def home():
    return "Instagram Downloader Bot is running!"


@app.post("/webhook")
def webhook():

    data = request.get_json(
        silent=True
    ) or {}

    # -------------------------------
    # INLINE BUTTON
    # -------------------------------

    callback = data.get("callback_query")

    if callback:

        callback_id = callback.get("id")

        callback_data = callback.get(
            "data",
            ""
        )

        message = callback.get(
            "message"
        )

        if message:

            chat = message.get(
                "chat"
            )

            if chat:

                handle_button(
                    chat["id"],
                    callback_id,
                    callback_data
                )

        return "OK"

    # -------------------------------
    # NORMAL MESSAGE
    # -------------------------------

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

    # /start
    if text == "/start":
        send_menu(chat_id)
        return "OK"

    # /help
    if text == "/help":
        send_help(chat_id)
        return "OK"

    # Instagram URL
    if not is_instagram_url(text):

        send_message(
            chat_id,
            "❌ Please send a valid public "
            "Instagram URL.\n\n"
            "Use /help for instructions."
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

        # --------------------------------
        # FIRST: yt-dlp
        # --------------------------------

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

            # ----------------------------
            # FALLBACK: parth-dl
            # ----------------------------

            send_message(
                chat_id,
                "🔄 Trying alternate "
                "Instagram media extractor..."
            )

            extractor_dir, files = (
                extract_instagram_media(text)
            )

        # --------------------------------
        # SEND FILES
        # --------------------------------

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
