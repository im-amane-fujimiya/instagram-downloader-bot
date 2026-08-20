import os
import subprocess
import tempfile
import shutil
import threading
import time

import requests
from flask import Flask, request

from extractor import extract_instagram_media, cleanup_media
from cleanup import schedule_delete

TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# =========================================================
# CONCURRENCY LIMIT
# =========================================================
# 0.1 vCPU / 512MB free-tier boxes can't handle two heavy
# yt-dlp/ffmpeg downloads running at the same time — RAM
# spikes and both requests slow to a crawl or crash.
# This semaphore forces downloads to run one at a time.
# Increase MAX_CONCURRENT_DOWNLOADS only if you move to a
# bigger instance.

MAX_CONCURRENT_DOWNLOADS = 1
download_semaphore = threading.Semaphore(MAX_CONCURRENT_DOWNLOADS)

# =========================================================
# INSTAGRAM COOLDOWN
# =========================================================
# Instagram rate-limits (429) IPs that hit it in bursts —
# shared hosting IPs (Render, etc.) get flagged faster since
# many bots share the same address range. Forcing a minimum
# gap between requests to Instagram makes traffic look less
# bursty and reduces how often we get blocked.

INSTAGRAM_COOLDOWN_SECONDS = 8
_last_instagram_request_lock = threading.Lock()
_last_instagram_request_time = 0.0


def wait_for_instagram_cooldown():
    global _last_instagram_request_time

    with _last_instagram_request_lock:
        now = time.monotonic()
        elapsed = now - _last_instagram_request_time
        remaining = INSTAGRAM_COOLDOWN_SECONDS - elapsed

        if remaining > 0:
            time.sleep(remaining)

        _last_instagram_request_time = time.monotonic()


# =========================================================
# BANNER
# =========================================================

BANNER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "1787159942996.png"
)


# =========================================================
# TELEGRAM COMMANDS + MENU
# =========================================================

def setup_bot_commands():

    commands = [
        {"command": "start", "description": "Start the downloader"},
        {"command": "download", "description": "Download Instagram media"},
        {"command": "help", "description": "How to use the bot"},
        {"command": "about", "description": "About this bot"}
    ]

    try:
        response = requests.post(
            f"{TELEGRAM_API}/setMyCommands",
            json={"commands": commands},
            timeout=30
        )
        print("SET COMMANDS:", response.text)

        response = requests.post(
            f"{TELEGRAM_API}/setChatMenuButton",
            json={"menu_button": {"type": "commands", "text": "Menu"}},
            timeout=30
        )
        print("SET MENU:", response.text)

    except Exception as error:
        print("COMMAND SETUP ERROR:", repr(error))


setup_bot_commands()


# =========================================================
# SEND MESSAGE
# =========================================================

def send_message(chat_id, text, reply_markup=None, parse_mode=None):

    data = {"chat_id": chat_id, "text": text}

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

    message_id = response.json()["result"]["message_id"]

    schedule_delete(TELEGRAM_API, chat_id, message_id)

    return message_id


# =========================================================
# DELETE MESSAGE
# =========================================================

def delete_message(chat_id, message_id):

    try:
        response = requests.post(
            f"{TELEGRAM_API}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
            timeout=30
        )

        if not response.ok:
            print("DELETE MESSAGE ERROR:", response.text)

    except Exception as error:
        print("DELETE MESSAGE ERROR:", repr(error))


# =========================================================
# ANSWER CALLBACK
# =========================================================

def answer_callback(callback_id):

    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=30
        )

    except Exception as error:
        print("CALLBACK ERROR:", repr(error))


# =========================================================
# START
# =========================================================

def send_start(chat_id):

    caption = (
        "👋 *Welcome to Instagram All-in-One!*\n\n"
        "🚀 Your simple sidekick for "
        "*Reels, Videos, Photos & Carousels.*\n\n"
        "😂 Instagram: “Save this post.”\n"
        "😎 Me: “Why save it when I can download it?”\n\n"
        "📥 Send me a public Instagram link "
        "and I'll handle the boring part.\n\n"
        "👇 Or use the buttons below."
    )

    try:
        if os.path.isfile(BANNER_PATH):

            with open(BANNER_PATH, "rb") as banner:

                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🎬 Reels", "callback_data": "reels"},
                            {"text": "🎥 Videos", "callback_data": "videos"}
                        ],
                        [
                            {"text": "🖼️ Photos", "callback_data": "photos"},
                            {"text": "📚 Carousel", "callback_data": "carousel"}
                        ],
                        [
                            {"text": "❓ Help", "callback_data": "help"}
                        ]
                    ]
                }

                response = requests.post(
                    f"{TELEGRAM_API}/sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "Markdown",
                        "reply_markup": str(keyboard).replace("'", '"')
                    },
                    files={"photo": banner},
                    timeout=60
                )

                response.raise_for_status()

        else:
            print("BANNER NOT FOUND:", BANNER_PATH)
            send_message(chat_id, caption, None, "Markdown")

    except Exception as error:
        print("START ERROR:", repr(error))
        send_menu(chat_id)


# =========================================================
# INLINE MENU
# =========================================================

def send_menu(chat_id):

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🎬 Reels", "callback_data": "reels"},
                {"text": "🎥 Videos", "callback_data": "videos"}
            ],
            [
                {"text": "🖼️ Photos", "callback_data": "photos"},
                {"text": "📚 Carousel", "callback_data": "carousel"}
            ],
            [
                {"text": "❓ Help", "callback_data": "help"}
            ]
        ]
    }

    send_message(
        chat_id,
        "📥 *Instagram Downloader*\n\n"
        "Send any public Instagram link and "
        "I'll handle the rest. 🚀\n\n"
        "Choose an option below:",
        keyboard,
        "Markdown"
    )


# =========================================================
# HELP
# =========================================================

def send_help(chat_id):

    keyboard = {
        "inline_keyboard": [
            [{"text": "📥 Download", "callback_data": "menu"}]
        ]
    }

    send_message(
        chat_id,
        "❓ *How to use Instagram All-in-One*\n\n"
        "1️⃣ Copy a public Instagram link.\n"
        "2️⃣ Send it to the bot.\n"
        "3️⃣ Wait while I fetch the media. 🚀\n\n"
        "✅ Reels\n"
        "✅ Videos\n"
        "✅ Photos\n"
        "✅ Carousels\n\n"
        "🔒 Private or login-protected content "
        "isn't supported.\n\n"
        "💡 Type / to see available commands.",
        keyboard,
        "Markdown"
    )


# =========================================================
# ABOUT
# =========================================================

def send_about(chat_id):

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📥 Download", "callback_data": "menu"},
                {"text": "❓ Help", "callback_data": "help"}
            ]
        ]
    }

    send_message(
        chat_id,
        "ℹ️ *Instagram All-in-One*\n\n"
        "A simple Telegram downloader for "
        "public Instagram media. 🚀\n\n"
        "🎬 Reels\n"
        "🎥 Videos\n"
        "🖼️ Photos\n"
        "📚 Carousels\n\n"
        "⚡ Simple\n"
        "🎯 Easy to use\n"
        "🤖 Automated\n\n"
        "Built to make saving public Instagram "
        "media a little less annoying. 😎",
        keyboard,
        "Markdown"
    )


# =========================================================
# SEND MEDIA
# =========================================================

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
            data={"chat_id": chat_id},
            files={field: media},
            timeout=120
        )

    response.raise_for_status()


# =========================================================
# YT-DLP
# =========================================================
# Format string caps resolution/filesize so a single request
# can't blow past the box's RAM/disk during download + mux.
# Prefers a pre-merged mp4 under 720p; falls back gracefully.

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
        "-f", YTDLP_FORMAT,
        "-o", output,
        url
    ]

    print("YTDLP:", " ".join(command))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180
    )

    print("YTDLP RETURN CODE:", result.returncode)
    print("YTDLP STDERR:", result.stderr[-2000:])

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
        raise Exception("yt-dlp finished but no media file was created.")

    return temp_dir, files


# =========================================================
# URL CHECK
# =========================================================

def is_instagram_url(url):
    return "instagram.com/" in url.lower()


# =========================================================
# BUTTON HANDLER
# =========================================================

def handle_button(chat_id, callback_id, action):

    answer_callback(callback_id)

    if action == "menu":
        send_menu(chat_id)

    elif action == "help":
        send_help(chat_id)

    elif action == "reels":
        send_message(
            chat_id,
            "🎬 *Reels mode ready!*\n\n"
            "Send a public Instagram Reel link. 🚀",
            None, "Markdown"
        )

    elif action == "videos":
        send_message(
            chat_id,
            "🎥 *Video mode ready!*\n\n"
            "Send a public Instagram video post link. 🚀",
            None, "Markdown"
        )

    elif action == "photos":
        send_message(
            chat_id,
            "🖼️ *Photos mode ready!*\n\n"
            "Send a public Instagram photo post link. 🚀",
            None, "Markdown"
        )

    elif action == "carousel":
        send_message(
            chat_id,
            "📚 *Carousel mode ready!*\n\n"
            "Send a public Instagram carousel link. 🚀",
            None, "Markdown"
        )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return "Instagram All-in-One Bot is running!"


# =========================================================
# WEBHOOK
# =========================================================

@app.post("/webhook")
def webhook():

    data = request.get_json(silent=True) or {}

    # =====================================================
    # INLINE BUTTON
    # =====================================================

    callback = data.get("callback_query")

    if callback:
        callback_id = callback.get("id")
        callback_data = callback.get("data", "")
        message = callback.get("message")

        if message:
            chat = message.get("chat")
            if chat:
                handle_button(chat["id"], callback_id, callback_data)

        return "OK"

    # =====================================================
    # NORMAL MESSAGE
    # =====================================================

    message = data.get("message")

    if not message:
        return "OK"

    chat = message.get("chat")
    text = message.get("text", "").strip()

    if not chat:
        return "OK"

    chat_id = chat["id"]

    if text == "/start":
        send_start(chat_id)
        return "OK"

    if text == "/help":
        send_help(chat_id)
        return "OK"

    if text == "/about":
        send_about(chat_id)
        return "OK"

    if text == "/download":
        send_message(
            chat_id,
            "📥 *Ready!*\n\n"
            "Send your public Instagram "
            "Reel, Video, Photo or Carousel link. 🚀",
            None, "Markdown"
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

    # =====================================================
    # BUSY CHECK — reject fast instead of queueing forever
    # =====================================================
    # If a download is already in progress on this small
    # instance, tell the new user to wait a bit instead of
    # silently piling up requests that would all compete for
    # the same 512MB.

    if not download_semaphore.acquire(blocking=False):
        send_message(
            chat_id,
            "⏳ *Thoda busy hoon abhi!*\n\n"
            "Ek aur download chal raha hai. "
            "Please 20-30 second baad try karo. 🙏",
            None, "Markdown"
        )
        return "OK"

    try:
        _handle_download(chat_id, text)
    finally:
        download_semaphore.release()

    return "OK"


def _handle_download(chat_id, text):

    loading_message_id = send_message(
        chat_id,
        "🔗 *Link received!*\n\n"
        "🔍 Checking the post...\n"
        "⚙️ Preparing your media...\n\n"
        "⏳ Hang tight, I'm on it 😎",
        None,
        "Markdown"
    )

    ytdlp_dir = None
    extractor_dir = None

    try:
        wait_for_instagram_cooldown()

        try:
            ytdlp_dir, files = download_with_ytdlp(text)
            print("yt-dlp succeeded:", files)

        except Exception as ytdlp_error:
            print("yt-dlp failed:", repr(ytdlp_error))

            send_message(
                chat_id,
                "🔄 Trying alternate "
                "Instagram media extractor..."
            )

            wait_for_instagram_cooldown()

            extractor_dir, files = extract_instagram_media(text)

        delete_message(chat_id, loading_message_id)

        sending_message_id = send_message(
            chat_id,
            "📤 *Sending your media...*",
            None,
            "Markdown"
        )

        sent = 0

        for filepath in files:
            try:
                send_media(chat_id, filepath)
                sent += 1

            except Exception as send_error:
                print("TELEGRAM SEND ERROR:", repr(send_error))

        delete_message(chat_id, sending_message_id)

        if sent == 0:
            raise Exception("No media could be sent to Telegram.")

        send_message(
            chat_id,
            f"🎉 *Done!*\n\n"
            f"📦 {sent} media file(s) delivered.\n"
            f"❤️ Enjoy!",
            None,
            "Markdown"
        )

    except subprocess.TimeoutExpired:
        delete_message(chat_id, loading_message_id)
        send_message(
            chat_id,
            "⏱️ *Download timed out.*\n\n"
            "Try a smaller public Instagram post. 😅",
            None,
            "Markdown"
        )

    except Exception as error:
        error_text = str(error)
        print("DOWNLOAD ERROR:", repr(error_text))

        delete_message(chat_id, loading_message_id)

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
            shutil.rmtree(ytdlp_dir, ignore_errors=True)

        if extractor_dir:
            cleanup_media(extractor_dir)
