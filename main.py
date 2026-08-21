import os
import subprocess
import tempfile
import shutil
import threading
import time
import json

import requests
from flask import Flask, request

from extractor import extract_instagram_media, cleanup_media
from cleanup import schedule_delete
from metadata import get_instagram_metadata


TOKEN = os.environ.get("BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

OWNER_CHAT_ID = os.environ.get(
    "OWNER_CHAT_ID",
    "-1002562168076"
)

app = Flask(__name__)

MAX_CONCURRENT_DOWNLOADS = 1
download_semaphore = threading.Semaphore(
    MAX_CONCURRENT_DOWNLOADS
)

INSTAGRAM_COOLDOWN_SECONDS = 15
_last_instagram_request_time = 0.0
_last_instagram_request_lock = threading.Lock()


def wait_for_instagram_cooldown():
    global _last_instagram_request_time

    with _last_instagram_request_lock:
        now = time.monotonic()
        elapsed = now - _last_instagram_request_time
        remaining = INSTAGRAM_COOLDOWN_SECONDS - elapsed

        if remaining > 0:
            time.sleep(remaining)

        _last_instagram_request_time = time.monotonic()


def send_message(
    chat_id,
    text,
    reply_markup=None,
    parse_mode=None
):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    if parse_mode:
        data["parse_mode"] = parse_mode

    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=data,
        timeout=30
    )

    response.raise_for_status()

    try:
        message_id = response.json()["result"]["message_id"]

        schedule_delete(
            TELEGRAM_API,
            chat_id,
            message_id
        )

        return message_id

    except Exception:
        return None


def delete_message(chat_id, message_id):
    if not message_id:
        return

    try:
        response = requests.post(
            f"{TELEGRAM_API}/deleteMessage",
            json={
                "chat_id": chat_id,
                "message_id": message_id
            },
            timeout=30
        )

        if not response.ok:
            print(
                "DELETE MESSAGE ERROR:",
                response.text
            )

    except Exception as error:
        print(
            "DELETE MESSAGE ERROR:",
            repr(error)
        )


def answer_callback(callback_id):
    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={
                "callback_query_id": callback_id
            },
            timeout=30
        )

    except Exception as error:
        print(
            "CALLBACK ERROR:",
            repr(error)
        )


def setup_bot_commands():
    commands = [
        {
            "command": "start",
            "description": "Start the downloader"
        },
        {
            "command": "download",
            "description": "Download Instagram media"
        },
        {
            "command": "help",
            "description": "How to use the bot"
        },
        {
            "command": "about",
            "description": "About this bot"
        }
    ]

    try:
        response = requests.post(
            f"{TELEGRAM_API}/setMyCommands",
            json={
                "commands": commands
            },
            timeout=30
        )

        print(
            "SET COMMANDS:",
            response.text
        )

        response = requests.post(
            f"{TELEGRAM_API}/setChatMenuButton",
            json={
                "menu_button": {
                    "type": "commands",
                    "text": "Menu"
                }
            },
            timeout=30
        )

        print(
            "SET MENU:",
            response.text
        )

    except Exception as error:
        print(
            "COMMAND SETUP ERROR:",
            repr(error)
        )


setup_bot_commands()


def send_start(chat_id):
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
        "👋 *Welcome to Instagram All-in-One!*\n\n"
        "🚀 Download public Instagram:\n"
        "🎬 Reels\n"
        "🎥 Videos\n"
        "🖼️ Photos\n"
        "📚 Carousels\n\n"
        "🔗 Send an Instagram link directly "
        "or use the buttons below.",
        keyboard,
        "Markdown"
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
        "📥 *Instagram Downloader*\n\n"
        "Send any public Instagram link.",
        keyboard,
        "Markdown"
    )


def send_help(chat_id):
    send_message(
        chat_id,
        "❓ *How to use*\n\n"
        "1️⃣ Copy a public Instagram link.\n"
        "2️⃣ Send it directly to the bot.\n"
        "3️⃣ Wait for the download.\n\n"
        "✅ Reels\n"
        "✅ Videos\n"
        "✅ Photos\n"
        "✅ Carousels\n\n"
        "🔒 Private/login-protected posts "
        "are not supported.",
        None,
        "Markdown"
    )


def send_about(chat_id):
    send_message(
        chat_id,
        "ℹ️ *Instagram All-in-One*\n\n"
        "A Telegram downloader for public "
        "Instagram media.\n\n"
        "🎬 Reels\n"
        "🎥 Videos\n"
        "🖼️ Photos\n"
        "📚 Carousels",
        None,
        "Markdown"
    )


def send_media(
    chat_id,
    filepath,
    caption=""
):
    extension = os.path.splitext(
        filepath
    )[1].lower()

    if extension in (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    ):
        method = "sendPhoto"
        field = "photo"

    elif extension in (
        ".mp4",
        ".mov",
        ".mkv",
        ".webm"
    ):
        method = "sendVideo"
        field = "video"

    else:
        method = "sendDocument"
        field = "document"

    data = {
        "chat_id": chat_id
    }

    if caption:
        data["caption"] = caption

    with open(
        filepath,
        "rb"
    ) as media:

        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            data=data,
            files={
                field: media
            },
            timeout=120
        )

    response.raise_for_status()


YTDLP_FORMAT = (
    "best[height<=720][filesize<80M]/"
    "best[height<=720]/"
    "best[filesize<80M]/"
    "best"
)


def download_with_ytdlp(url):
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
        "-f",
        YTDLP_FORMAT,
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

    for filename in os.listdir(
        temp_dir
    ):
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
            "yt-dlp finished but no media file "
            "was created."
        )

    return temp_dir, files


def is_instagram_url(url):
    return (
        "instagram.com/" in
        url.lower()
    )


def handle_button(
    chat_id,
    callback_id,
    action
):
    answer_callback(
        callback_id
    )

    if action == "menu":
        send_menu(chat_id)

    elif action == "help":
        send_help(chat_id)

    elif action == "reels":
        send_message(
            chat_id,
            "🎬 *Reels mode ready!*\n\n"
            "Send the Instagram Reel link.",
            None,
            "Markdown"
        )

    elif action == "videos":
        send_message(
            chat_id,
            "🎥 *Video mode ready!*\n\n"
            "Send the Instagram video link.",
            None,
            "Markdown"
        )

    elif action == "photos":
        send_message(
            chat_id,
            "🖼️ *Photo mode ready!*\n\n"
            "Send the Instagram photo link.",
            None,
            "Markdown"
        )

    elif action == "carousel":
        send_message(
            chat_id,
            "📚 *Carousel mode ready!*\n\n"
            "Send the Instagram carousel link.",
            None,
            "Markdown"
        )


def build_caption(metadata):
    title = (
        metadata.get("title") or ""
    ).strip()

    description = (
        metadata.get("description") or ""
    ).strip()

    parts = []

    if title:
        parts.append(
            f"📝 {title}"
        )

    if description:
        parts.append(
            f"📄 {description}"
        )

    caption = "\n\n".join(parts)

    return caption[:1024]


def process_download(
    chat_id,
    url
):
    loading_message_id = send_message(
        chat_id,
        "🔗 *Link received!*\n\n"
        "🔍 Fetching your media...\n"
        "⏳ Please wait...",
        None,
        "Markdown"
    )

    ytdlp_dir = None
    extractor_dir = None

    try:
        print(
            "METADATA: fetching..."
        )

        metadata = get_instagram_metadata(
            url
        )

        print(
            "METADATA:",
            metadata
        )

        wait_for_instagram_cooldown()

        try:
            ytdlp_dir, files = (
                download_with_ytdlp(
                    url
                )
            )

            print(
                "yt-dlp succeeded:",
                files
            )

        except Exception as error:
            print(
                "yt-dlp failed:",
                repr(error)
            )

            send_message(
                chat_id,
                "🔄 Trying alternate downloader..."
            )

            wait_for_instagram_cooldown()

            extractor_dir, files = (
                extract_instagram_media(
                    url
                )
            )

        delete_message(
            chat_id,
            loading_message_id
        )

        caption = build_caption(
            metadata
        )

        sent = 0

        for filepath in files:
            try:
                send_media(
                    chat_id,
                    filepath,
                    caption if sent == 0 else ""
                )

                sent += 1

            except Exception as error:
                print(
                    "SEND MEDIA ERROR:",
                    repr(error)
                )

        if sent == 0:
            raise Exception(
                "No media could be sent."
            )

        if not caption:
            send_message(
                chat_id,
                "✅ *Download complete!*",
                None,
                "Markdown"
            )

    except subprocess.TimeoutExpired:
        delete_message(
            chat_id,
            loading_message_id
        )

        send_message(
            chat_id,
            "⏱️ *Download timed out.*\n\n"
            "Please try again.",
            None,
            "Markdown"
        )

    except Exception as error:
        print(
            "DOWNLOAD ERROR:",
            repr(error)
        )

        delete_message(
            chat_id,
            loading_message_id
        )

        send_message(
            chat_id,
            "😬 *Instagram ne thoda nakhra "
            "dikha diya.*\n\n"
            "🔄 Please try again in a moment.",
            None,
            "Markdown"
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


@app.get("/")
def home():
    return "Instagram All-in-One Bot is running!"


@app.post("/")
@app.post("/webhook")
def webhook():
    data = (
        request.get_json(
            silent=True
        ) or {}
    )

    callback = data.get(
        "callback_query"
    )

    if callback:
        callback_id = callback.get(
            "id"
        )

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

    message = data.get(
        "message"
    )

    if not message:
        return "OK"

    chat = message.get(
        "chat"
    )

    if not chat:
        return "OK"

    chat_id = chat["id"]

    text = (
        message.get(
            "text",
            ""
        ).strip()
    )

    if not text:
        return "OK"

    cmd = (
        text.split()[0]
        .lower()
        .split("@")[0]
    )

    if cmd == "/start":
        send_start(chat_id)
        return "OK"

    if cmd == "/help":
        send_help(chat_id)
        return "OK"

    if cmd == "/about":
        send_about(chat_id)
        return "OK"

    if cmd == "/download":
        send_message(
            chat_id,
            "📥 *Ready!*\n\n"
            "Send a public Instagram link.",
            None,
            "Markdown"
        )
        return "OK"

    if not is_instagram_url(text):
        send_message(
            chat_id,
            "🤔 Hmm... mujhe ye samajh nahi aaya.\n\n"
            "🔗 Instagram link bhejo, "
            "ya /help use karo. 😎"
        )
        return "OK"

    if not download_semaphore.acquire(
        blocking=False
    ):
        send_message(
            chat_id,
            "⏳ *Downloader busy hai.*\n\n"
            "Thodi der baad try karo.",
            None,
            "Markdown"
        )
        return "OK"

    try:
        process_download(
            chat_id,
            text
        )

    finally:
        download_semaphore.release()

    return "OK"


if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
        )
