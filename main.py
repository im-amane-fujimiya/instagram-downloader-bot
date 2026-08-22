import html
import os
import threading
import time

import requests
from flask import Flask, request

from config import (
    BOT_TOKEN,
    TELEGRAM_API,
    OWNER_CHAT_ID,
    PORT,
    BANNER_PATH,
    INSTAGRAM_COOLDOWN_SECONDS,
)

from extractor import (
    download_instagram_media,
    get_instagram_metadata,
    cleanup_media,
)

from media import (
    send_media,
)

from cleanup import (
    delete_message,
    schedule_delete,
)


# =========================================================
# APP
# =========================================================

app = Flask(__name__)


# =========================================================
# STATE
# =========================================================

START_TIME = time.monotonic()

_download_lock = threading.Lock()

_last_download_time = 0.0

_stats_lock = threading.Lock()

TOTAL_DOWNLOADS = 0

USER_DOWNLOADS = {}


# =========================================================
# INSTAGRAM COOLDOWN
# =========================================================

def wait_for_instagram():

    global _last_download_time

    with _download_lock:

        now = time.monotonic()

        elapsed = (
            now - _last_download_time
        )

        remaining = (
            INSTAGRAM_COOLDOWN_SECONDS
            - elapsed
        )

        if remaining > 0:

            time.sleep(
                remaining
            )

        _last_download_time = (
            time.monotonic()
        )


# =========================================================
# TELEGRAM REQUEST
# =========================================================

def telegram(
    method,
    payload=None,
    files=None,
    timeout=30,
):

    response = requests.post(
        f"{TELEGRAM_API}/{method}",
        data=payload,
        files=files,
        timeout=timeout,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):

        raise RuntimeError(
            result.get(
                "description",
                "Telegram API error."
            )
        )

    return result.get(
        "result"
    )


# =========================================================
# SEND MESSAGE
# =========================================================

def send_message(
    chat_id,
    text,
    reply_markup=None,
    parse_mode="HTML",
    auto_delete=True,
):

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if parse_mode:

        payload["parse_mode"] = (
            parse_mode
        )

    if reply_markup:

        payload["reply_markup"] = (
            reply_markup
        )

    result = telegram(
        "sendMessage",
        payload=payload,
    )

    message_id = result[
        "message_id"
    ]

    if auto_delete:

        schedule_delete(
            TELEGRAM_API,
            chat_id,
            message_id,
        )

    return message_id


# =========================================================
# BUTTONS
# =========================================================

def main_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🎬 Reels",
                    "callback_data": "reels",
                },
                {
                    "text": "🎥 Videos",
                    "callback_data": "videos",
                },
            ],
            [
                {
                    "text": "🖼️ Photos",
                    "callback_data": "photos",
                },
                {
                    "text": "📚 Carousel",
                    "callback_data": "carousel",
                },
            ],
            [
                {
                    "text": "❓ Help",
                    "callback_data": "help",
                },
                {
                    "text": "ℹ️ About",
                    "callback_data": "about",
                },
            ],
        ]
    }


# =========================================================
# CALLBACK ANSWER
# =========================================================

def answer_callback(
    callback_id
):

    try:

        telegram(
            "answerCallbackQuery",
            payload={
                "callback_query_id":
                    callback_id,
            },
        )

    except Exception as error:

        print(
            "CALLBACK ERROR:",
            repr(error),
        )


# =========================================================
# START
# =========================================================

def send_start(chat_id):

    text = (
        "👋 <b>Welcome to Instagram All-in-One!</b>\n\n"

        "🚀 Download public Instagram "
        "<b>Reels, Videos, Photos & Carousels.</b>\n\n"

        "😂 Instagram: “Save this post.”\n"
        "😎 Me: “Why save it when I can download it?”\n\n"

        "📥 Send me a public Instagram link "
        "and I'll handle the boring part.\n\n"

        "👇 Choose an option below."
    )

    if os.path.isfile(BANNER_PATH):

        try:

            with open(
                BANNER_PATH,
                "rb"
            ) as banner:

                result = telegram(
                    "sendPhoto",
                    payload={
                        "chat_id":
                            chat_id,

                        "caption":
                            text,

                        "parse_mode":
                            "HTML",

                        "reply_markup":
                            str(
                                main_keyboard()
                            ).replace(
                                "'",
                                '"'
                            ),
                    },
                    files={
                        "photo":
                            banner,
                    },
                    timeout=60,
                )

            schedule_delete(
                TELEGRAM_API,
                chat_id,
                result["message_id"],
            )

            return

        except Exception as error:

            print(
                "BANNER ERROR:",
                repr(error),
            )

    send_message(
        chat_id,
        text,
        main_keyboard(),
    )


# =========================================================
# HELP
# =========================================================

def send_help(chat_id):

    text = (
        "❓ <b>How to use</b>\n\n"

        "1️⃣ Copy a public Instagram link.\n"
        "2️⃣ Send it here.\n"
        "3️⃣ Wait while the media is downloaded.\n\n"

        "✅ Reels\n"
        "✅ Videos\n"
        "✅ Photos\n"
        "✅ Carousels\n\n"

        "🔒 Private/login-protected posts "
        "are not supported."
    )

    send_message(
        chat_id,
        text,
        main_keyboard(),
    )


# =========================================================
# ABOUT
# =========================================================

def send_about(chat_id):

    text = (
        "ℹ️ <b>Instagram All-in-One</b>\n\n"

        "A simple Telegram downloader for "
        "public Instagram media.\n\n"

        "🎬 Reels\n"
        "🎥 Videos\n"
        "🖼️ Photos\n"
        "📚 Carousels\n\n"

        "⚡ Fast • Simple • Automated"
    )

    send_message(
        chat_id,
        text,
        main_keyboard(),
    )


# =========================================================
# PING
# =========================================================

def send_ping(chat_id):

    uptime = int(
        time.monotonic()
        - START_TIME
    )

    hours = uptime // 3600

    minutes = (
        uptime % 3600
    ) // 60

    seconds = (
        uptime % 60
    )

    with _stats_lock:

        total = TOTAL_DOWNLOADS

        users = len(
            USER_DOWNLOADS
        )

    text = (
        "🏓 <b>Pong!</b>\n\n"

        "🟢 Status: <b>Online</b>\n"
        f"⏱️ Uptime: <b>"
        f"{hours}h {minutes}m {seconds}s"
        f"</b>\n"
        f"📥 Downloads: <b>{total}</b>\n"
        f"👥 Users: <b>{users}</b>"
    )

    send_message(
        chat_id,
        text,
        None,
        auto_delete=False,
    )


# =========================================================
# STATS
# =========================================================

def record_download(
    chat_id
):

    global TOTAL_DOWNLOADS

    with _stats_lock:

        TOTAL_DOWNLOADS += 1

        key = str(
            chat_id
        )

        USER_DOWNLOADS[key] = (
            USER_DOWNLOADS.get(
                key,
                0
            ) + 1
        )


def send_stats(chat_id):

    with _stats_lock:

        total = TOTAL_DOWNLOADS

        users = len(
            USER_DOWNLOADS
        )

        mine = USER_DOWNLOADS.get(
            str(chat_id),
            0
        )

    text = (
        "📊 <b>Bot Stats</b>\n\n"
        f"📥 Total downloads: <b>{total}</b>\n"
        f"👥 Unique users: <b>{users}</b>\n"
        f"🙋 Your downloads: <b>{mine}</b>"
    )

    send_message(
        chat_id,
        text,
        None,
        auto_delete=False,
    )


# =========================================================
# URL CHECK
# =========================================================

def is_instagram_url(
    url
):

    value = url.lower()

    return (
        "instagram.com/" in value
        or
        "instagr.am/" in value
    )


# =========================================================
# METADATA CAPTION
# =========================================================

def build_metadata_caption(
    metadata
):

    if not metadata:

        return None

    title = (
        metadata.get("title")
        or ""
    ).strip()

    description = (
        metadata.get("description")
        or ""
    ).strip()

    uploader = (
        metadata.get("uploader")
        or ""
    ).strip()

    # Avoid sending duplicate title
    # when yt-dlp returns caption as title.
    if title and description:

        if title.strip() == description.strip():

            description = ""

    parts = []

    if uploader:

        parts.append(
            f"👤 <b>{html.escape(uploader)}</b>"
        )

    if title:

        parts.append(
            "📝 <b>"
            + html.escape(title[:500])
            + "</b>"
        )

    if description:

        parts.append(
            "💬 "
            + html.escape(
                description[:700]
            )
        )

    if not parts:

        return None

    caption = "\n\n".join(
        parts
    )

    # Telegram caption limit safety.
    return caption[:1000]


# =========================================================
# DOWNLOAD
# =========================================================

def process_download(
    chat_id,
    url
):

    loading_id = None

    temp_dir = None

    try:

        loading_id = send_message(
            chat_id,
            "⏳ <b>Fetching Instagram media...</b>\n\n"
            "Please wait.",
            None,
            auto_delete=False,
        )

        # -------------------------------------------------
        # Metadata
        # -------------------------------------------------

        metadata = {}

        try:

            metadata = (
                get_instagram_metadata(
                    url
                )
            )

            print(
                "METADATA:",
                metadata,
            )

        except Exception as error:

            print(
                "METADATA FAILED:",
                repr(error),
            )

        # -------------------------------------------------
        # Cooldown
        # -------------------------------------------------

        wait_for_instagram()

        # -------------------------------------------------
        # Download
        # -------------------------------------------------

        temp_dir, files = (
            download_instagram_media(
                url
            )
        )

        # -------------------------------------------------
        # Remove loading
        # -------------------------------------------------

        if loading_id:

            delete_message(
                chat_id,
                loading_id,
            )

            loading_id = None

        # -------------------------------------------------
        # Caption
        # -------------------------------------------------

        caption = (
            build_metadata_caption(
                metadata
            )
        )

        # -------------------------------------------------
        # Send files
        # -------------------------------------------------

        sent = 0

        for index, filepath in enumerate(
            files
        ):

            try:

                current_caption = None

                # Caption only on first file.
                if index == 0:

                    current_caption = caption

                send_media(
                    chat_id,
                    filepath,
                    current_caption,
                )

                sent += 1

            except Exception as error:

                print(
                    "MEDIA SEND ERROR:",
                    repr(error),
                )

                send_message(
                    chat_id,
                    "⚠️ One media file could "
                    "not be sent.",
                    None,
                )

        if sent == 0:

            raise RuntimeError(
                "Downloaded media could not "
                "be sent to Telegram."
            )

        record_download(
            chat_id
        )

        # -------------------------------------------------
        # Success
        # -------------------------------------------------

        if len(files) > 1:

            send_message(
                chat_id,
                f"✅ <b>Done!</b>\n\n"
                f"📦 {sent} media files sent.",
                None,
                auto_delete=False,
            )

        else:

            send_message(
                chat_id,
                "✅ <b>Done!</b>",
                None,
                auto_delete=False,
            )

    except Exception as error:

        print(
            "DOWNLOAD ERROR:",
            repr(error),
        )

        if loading_id:

            delete_message(
                chat_id,
                loading_id,
            )

        send_message(
            chat_id,
            "😬 <b>Download failed.</b>\n\n"
            "Make sure the Instagram post is "
            "public and the link is valid.\n\n"
            "🔄 Please try again.",
            None,
        )

    finally:

        if temp_dir:

            cleanup_media(
                temp_dir
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

    if action == "help":

        send_help(
            chat_id
        )

        return

    if action == "about":

        send_about(
            chat_id
        )

        return

    messages = {
        "reels":
            "🎬 <b>Reels mode ready!</b>\n\n"
            "Send a public Instagram Reel link.",

        "videos":
            "🎥 <b>Video mode ready!</b>\n\n"
            "Send a public Instagram video link.",

        "photos":
            "🖼️ <b>Photo mode ready!</b>\n\n"
            "Send a public Instagram photo link.",

        "carousel":
            "📚 <b>Carousel mode ready!</b>\n\n"
            "Send a public Instagram carousel link.",
    }

    if action in messages:

        send_message(
            chat_id,
            messages[action],
            main_keyboard(),
        )


# =========================================================
# COMMAND SETUP
# =========================================================

def setup_commands():

    commands = [
        {
            "command": "start",
            "description": "Start the downloader",
        },
        {
            "command": "download",
            "description": "Download Instagram media",
        },
        {
            "command": "ping",
            "description": "Check bot status",
        },
        {
            "command": "stats",
            "description": "Show download stats",
        },
        {
            "command": "help",
            "description": "How to use the bot",
        },
        {
            "command": "about",
            "description": "About this bot",
        },
    ]

    try:

        result = telegram(
            "setMyCommands",
            payload={
                "commands":
                    __import__(
                        "json"
                    ).dumps(commands)
            },
        )

        print(
            "SET COMMANDS:",
            result,
        )

    except Exception as error:

        print(
            "COMMAND SETUP ERROR:",
            repr(error),
        )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return (
        "Instagram All-in-One Bot is running!"
    )


# =========================================================
# WEBHOOK
# =========================================================

@app.post("/")
@app.post("/webhook")
def webhook():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    # =====================================================
    # CALLBACK
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
                    callback_data,
                )

        return "OK"


    # =====================================================
    # MESSAGE
    # =====================================================

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
        )
        .strip()
    )

    if not text:

        return "OK"


    # =====================================================
    # COMMAND
    # =====================================================

    first_word = (
        text.split()[0]
        if text
        else ""
    )

    command = (
        first_word
        .lower()
        .split("@")[0]
    )


    # =====================================================
    # /START
    # =====================================================

    if command == "/start":

        send_start(
            chat_id
        )

        return "OK"


    # =====================================================
    # /HELP
    # =====================================================

    if command == "/help":

        send_help(
            chat_id
        )

        return "OK"


    # =====================================================
    # /ABOUT
    # =====================================================

    if command == "/about":

        send_about(
            chat_id
        )

        return "OK"


    # =====================================================
    # /PING
    # =====================================================

    if command == "/ping":

        send_ping(
            chat_id
        )

        return "OK"


    # =====================================================
    # /STATS
    # =====================================================

    if command == "/stats":

        send_stats(
            chat_id
        )

        return "OK"


    # =====================================================
    # /DOWNLOAD
    # =====================================================

    if command == "/download":

        send_message(
            chat_id,
            "📥 <b>Send me a public Instagram link.</b>",
            None,
        )

        return "OK"


    # =====================================================
    # INSTAGRAM URL
    # =====================================================

    if is_instagram_url(text):

        threading.Thread(
            target=process_download,
            args=(
                chat_id,
                text,
            ),
            daemon=True,
        ).start()

        return "OK"


    # =====================================================
    # UNKNOWN TEXT
    # =====================================================

    send_message(
        chat_id,
        "📥 Send a public Instagram link "
        "to start downloading.",
        main_keyboard(),
    )

    return "OK"


# =========================================================
# STARTUP
# =========================================================

setup_commands()


# =========================================================
# SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        )
