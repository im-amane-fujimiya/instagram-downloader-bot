import os
import json
import subprocess
import tempfile
import shutil

import requests
from flask import Flask, request

from extractor import extract_instagram_media, cleanup_media


TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# =========================================================
# BANNER
# =========================================================

BANNER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "1787159942996.png"
)


# =========================================================
# TELEGRAM COMMANDS
# =========================================================

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

        # Telegram Menu button
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


# =========================================================
# BOTTOM KEYBOARD
# =========================================================

def bottom_keyboard():

    return {
        "keyboard": [
            [
                "📥 Download",
                "❓ Help"
            ],
            [
                "🎬 Reels",
                "🎥 Videos"
            ],
            [
                "🖼️ Photos",
                "📚 Carousel"
            ],
            [
                "ℹ️ About"
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "Send an Instagram link..."
    }


# =========================================================
# SEND MESSAGE
# =========================================================

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


# =========================================================
# ANSWER CALLBACK
# =========================================================

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


# =========================================================
# START SCREEN
# =========================================================

def send_start(chat_id):

    keyboard = bottom_keyboard()

    caption = (
        "👋 *Welcome to Instagram All-in-One!*\n\n"

        "🚀 Your simple little sidekick for "
        "*Reels, Videos, Photos & Carousels.*\n\n"

        "😂 Instagram: “Save this post.”\n"
        "😎 Me: “Why save it when I can download it?”\n\n"

        "📥 Just send me a public Instagram link "
        "and let me do the boring part.\n\n"

        "👇 Pick an option below or simply "
        "send your link."
    )

    try:

        if os.path.isfile(BANNER_PATH):

            with open(
                BANNER_PATH,
                "rb"
            ) as banner:

                response = requests.post(
                    f"{TELEGRAM_API}/sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "Markdown",
                        "reply_markup": json.dumps(
                            keyboard
                        )
                    },
                    files={
                        "photo": banner
                    },
                    timeout=60
                )

                response.raise_for_status()

        else:

            print(
                "BANNER NOT FOUND:",
                BANNER_PATH
            )

            send_message(
                chat_id,
                caption,
                keyboard,
                "Markdown"
            )

    except Exception as error:

        print(
            "START ERROR:",
            repr(error)
        )

        # Fallback:
        # Even if banner fails, bot still sends
        # the welcome message + keyboard.

        send_message(
            chat_id,
            caption,
            keyboard,
            "Markdown"
        )


# =========================================================
# INLINE MENU
# =========================================================

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
        "Send any public Instagram link and "
        "I'll handle the rest. 🚀\n\n"
        "Choose a category below:",
        keyboard,
        "Markdown"
    )


# =========================================================
# HELP
# =========================================================

def send_help(chat_id):

    send_message(
        chat_id,

        "❓ *How to use Instagram All-in-One*\n\n"

        "1️⃣ Copy a public Instagram link.\n"
        "2️⃣ Send it to me.\n"
        "3️⃣ Wait while I fetch the media. 🚀\n\n"

        "✅ Reels\n"
        "✅ Videos\n"
        "✅ Photos\n"
        "✅ Carousels\n\n"

        "🔒 Private or login-protected content "
        "isn't supported.\n\n"

        "💡 *Tip:* You can use the buttons below "
        "or simply paste a link.",

        bottom_keyboard(),
        "Markdown"
    )


# =========================================================
# ABOUT
# =========================================================

def send_about(chat_id):

    send_message(
        chat_id,

        "ℹ️ *About Instagram All-in-One*\n\n"

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

        bottom_keyboard(),
        "Markdown"
    )


# =========================================================
# SEND MEDIA
# =========================================================

def send_media(chat_id, filepath):

    extension = os.path.splitext(
        filepath
    )[1].lower()

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

    with open(
        filepath,
        "rb"
    ) as media:

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


# =========================================================
# YT-DLP
# =========================================================

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
            "yt-dlp finished but no media file was created."
        )

    return temp_dir, files


# =========================================================
# URL CHECK
# =========================================================

def is_instagram_url(url):

    return (
        "instagram.com/" in url.lower()
    )


# =========================================================
# BUTTON HANDLER
# =========================================================

def handle_button(
    chat_id,
    callback_id,
    action
):

    answer_callback(
        callback_id
    )

    if action == "menu":

        send_menu(
            chat_id
        )

    elif action == "help":

        send_help(
            chat_id
        )

    elif action == "reels":

        send_message(
            chat_id,
            "🎬 *Reels mode ready!*\n\n"
            "Send a public Instagram Reel link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

    elif action == "videos":

        send_message(
            chat_id,
            "🎥 *Video mode ready!*\n\n"
            "Send a public Instagram video post link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

    elif action == "photos":

        send_message(
            chat_id,
            "🖼️ *Photo mode ready!*\n\n"
            "Send a public Instagram photo post link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

    elif action == "carousel":

        send_message(
            chat_id,
            "📚 *Carousel mode ready!*\n\n"
            "Send a public Instagram carousel link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return (
        "Instagram All-in-One Bot "
        "is running!"
    )


# =========================================================
# WEBHOOK
# =========================================================

@app.post("/webhook")
def webhook():

    data = request.get_json(
        silent=True
    ) or {}

    # =====================================================
    # CALLBACK / INLINE BUTTON
    # =====================================================

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

    # =====================================================
    # NORMAL MESSAGE
    # =====================================================

    message = data.get(
        "message"
    )

    if not message:

        return "OK"

    chat = message.get(
        "chat"
    )

    text = message.get(
        "text",
        ""
    ).strip()

    if not chat:

        return "OK"

    chat_id = chat["id"]

    # =====================================================
    # START
    # =====================================================

    if text == "/start":

        send_start(
            chat_id
        )

        return "OK"

    # =====================================================
    # HELP
    # =====================================================

    if text == "/help":

        send_help(
            chat_id
        )

        return "OK"

    # =====================================================
    # ABOUT
    # =====================================================

    if text == "/about":

        send_about(
            chat_id
        )

        return "OK"

    # =====================================================
    # DOWNLOAD
    # =====================================================

    if text == "/download":

        send_message(
            chat_id,
            "📥 *Ready!*\n\n"
            "Send your public Instagram "
            "Reel, Video, Photo or Carousel link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

        return "OK"

    # =====================================================
    # BOTTOM KEYBOARD
    # =====================================================

    if text == "📥 Download":

        send_message(
            chat_id,
            "📥 *Send the Instagram link!* 🔗\n\n"
            "I'll take care of the boring part. 😎",
            bottom_keyboard(),
            "Markdown"
        )

        return "OK"

    if text == "❓ Help":

        send_help(
            chat_id
        )

        return "OK"

    if text == "🎬 Reels":

        send_message(
            chat_id,
            "🎬 *Reels mode ready!*\n\n"
            "Send a public Instagram Reel link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

        return "OK"

    if text == "🎥 Videos":

        send_message(
            chat_id,
            "🎥 *Videos mode ready!*\n\n"
            "Send a public Instagram video post link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

        return "OK"

    if text == "🖼️ Photos":

        send_message(
            chat_id,
            "🖼️ *Photos mode ready!*\n\n"
            "Send a public Instagram photo post link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

        return "OK"

    if text == "📚 Carousel":

        send_message(
            chat_id,
            "📚 *Carousel mode ready!*\n\n"
            "Send a public Instagram carousel link. 🚀",
            bottom_keyboard(),
            "Markdown"
        )

        return "OK"

    if text == "ℹ️ About":

        send_about(
            chat_id
        )

        return "OK"

    # =====================================================
    # INSTAGRAM URL
    # =====================================================

    if not is_instagram_url(text):

        send_message(
            chat_id,
            "🤔 Hmm... mujhe ye samajh nahi aaya.\n\n"
            "🔗 Instagram link bhejo, "
            "ya neeche se koi option choose karo. 😎",
            bottom_keyboard()
        )

        return "OK"

    # =====================================================
    # DOWNLOAD START
    # =====================================================

    send_message(
        chat_id,
        "🔍 *Link detected!*\n\n"
        "📡 Fetching media...\n"
        "⚙️ Processing...\n"
        "⏳ Please wait...",
        bottom_keyboard(),
        "Markdown"
    )

    ytdlp_dir = None
    extractor_dir = None

    try:

        # =================================================
        # FIRST: YT-DLP
        # =================================================

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

            send_message(
                chat_id,
                "🔄 Trying alternate "
                "Instagram media extractor..."
            )

            # =============================================
            # FALLBACK: EXTRACTOR.PY
            # =============================================

            extractor_dir, files = (
                extract_instagram_media(text)
            )

        # =================================================
        # SEND FILES
        # =================================================

        send_message(
            chat_id,
            "📤 *Sending your media...*",
            None,
            "Markdown"
        )

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
            f"🎉 *Done!*\n\n"
            f"📦 {sent} media file(s) delivered.\n"
            f"❤️ Enjoy!",
            bottom_keyboard(),
            "Markdown"
        )

    except subprocess.TimeoutExpired:

        send_message(
            chat_id,
            "⏱️ *Download timed out.*\n\n"
            "Try a smaller public Instagram post. 😅",
            bottom_keyboard(),
            "Markdown"
        )

    except Exception as error:

        error_text = str(error)

        print(
            "DOWNLOAD ERROR:",
            repr(error_text)
        )

        send_message(
            chat_id,
            "😬 *Instagram ne thoda nakhra "
            "dikha diya.*\n\n"
            "🔄 Please try again in a moment.",
            bottom_keyboard(),
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

    return "ok"
