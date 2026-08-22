import html
import json
import os
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

from media import send_media

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

_last_download_time = 0.0

TOTAL_DOWNLOADS = 0

USER_DOWNLOADS = {}


# =========================================================
# INSTAGRAM COOLDOWN
# =========================================================

def wait_for_instagram():
    """
    Keeps a small delay between Instagram download attempts.

    Note:
    On Vercel, different serverless instances can have separate
    memory, so this is not a global distributed rate limiter.
    """

    global _last_download_time

    now = time.monotonic()

    elapsed = now - _last_download_time

    remaining = (
        INSTAGRAM_COOLDOWN_SECONDS
        - elapsed
    )

    if remaining > 0:
        time.sleep(remaining)

    _last_download_time = time.monotonic()


# =========================================================
# TELEGRAM REQUEST
# =========================================================

def telegram(
    method,
    payload=None,
    files=None,
    timeout=30,
):
    """
    Central Telegram API helper.
    """

    url = f"{TELEGRAM_API}/{method}"

    response = requests.post(
        url,
        data=payload,
        files=files,
        timeout=timeout,
    )

    # -----------------------------------------------------
    # HTTP ERROR
    # -----------------------------------------------------

    if not response.ok:

        print(
            "TELEGRAM HTTP ERROR:",
            response.status_code,
            response.text[:2000],
        )

        response.raise_for_status()

    # -----------------------------------------------------
    # JSON
    # -----------------------------------------------------

    try:

        result = response.json()

    except Exception:

        print(
            "TELEGRAM INVALID JSON:",
            response.text[:2000],
        )

        raise RuntimeError(
            "Telegram returned an invalid response."
        )

    # -----------------------------------------------------
    # TELEGRAM API ERROR
    # -----------------------------------------------------

    if not result.get("ok"):

        description = result.get(
            "description",
            "Telegram API error.",
        )

        print(
            "TELEGRAM API ERROR:",
            method,
            description,
        )

        raise RuntimeError(
            description
        )

    return result.get("result")


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
    """
    Sends a Telegram message.

    IMPORTANT:
    reply_markup must be JSON encoded before being sent.
    """

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    # -----------------------------------------------------
    # PARSE MODE
    # -----------------------------------------------------

    if parse_mode:

        payload["parse_mode"] = parse_mode

    # -----------------------------------------------------
    # KEYBOARD
    # -----------------------------------------------------

    if reply_markup:

        payload["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False,
        )

    # -----------------------------------------------------
    # SEND
    # -----------------------------------------------------

    result = telegram(
        "sendMessage",
        payload=payload,
    )

    if not result:

        raise RuntimeError(
            "Telegram did not return a message."
        )

    message_id = result.get(
        "message_id"
    )

    # -----------------------------------------------------
    # AUTO DELETE
    # -----------------------------------------------------

    if auto_delete and message_id:

        try:

            schedule_delete(
                TELEGRAM_API,
                chat_id,
                message_id,
            )

        except Exception as error:

            print(
                "SCHEDULE DELETE ERROR:",
                repr(error),
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

def answer_callback(callback_id):

    if not callback_id:

        return

    try:

        telegram(
            "answerCallbackQuery",
            payload={
                "callback_query_id": callback_id,
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

    # -----------------------------------------------------
    # BANNER
    # -----------------------------------------------------

    if os.path.isfile(BANNER_PATH):

        try:

            with open(
                BANNER_PATH,
                "rb",
            ) as banner:

                result = telegram(
                    "sendPhoto",
                    payload={
                        "chat_id": chat_id,

                        "caption": text,

                        "parse_mode": "HTML",

                        "reply_markup": json.dumps(
                            main_keyboard(),
                            ensure_ascii=False,
                        ),
                    },
                    files={
                        "photo": banner,
                    },
                    timeout=60,
                )

            if result and result.get("message_id"):

                try:

                    schedule_delete(
                        TELEGRAM_API,
                        chat_id,
                        result["message_id"],
                    )

                except Exception as error:

                    print(
                        "BANNER DELETE SCHEDULE ERROR:",
                        repr(error),
                    )

            return

        except Exception as error:

            print(
                "BANNER ERROR:",
                repr(error),
            )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

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

def record_download(chat_id):

    global TOTAL_DOWNLOADS

    TOTAL_DOWNLOADS += 1

    key = str(chat_id)

    USER_DOWNLOADS[key] = (
        USER_DOWNLOADS.get(
            key,
            0,
        )
        + 1
    )


def send_stats(chat_id):

    total = TOTAL_DOWNLOADS

    users = len(
        USER_DOWNLOADS
    )

    mine = USER_DOWNLOADS.get(
        str(chat_id),
        0,
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

def is_instagram_url(url):

    if not url:

        return False

    value = url.lower().strip()

    return (
        "instagram.com/" in value
        or
        "instagr.am/" in value
    )


# =========================================================
# METADATA CAPTION
# =========================================================

def build_metadata_caption(metadata):

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

    # -----------------------------------------------------
    # Avoid duplicate title/description
    # -----------------------------------------------------

    if (
        title
        and description
        and title == description
    ):

        description = ""

    parts = []

    # -----------------------------------------------------
    # USERNAME
    # -----------------------------------------------------

    if uploader:

        parts.append(
            "👤 <b>"
            + html.escape(
                uploader
            )
            + "</b>"
        )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    if title:

        parts.append(
            "📝 <b>"
            + html.escape(
                title[:500]
            )
            + "</b>"
        )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    if description:

        parts.append(
            "💬 "
            + html.escape(
                description[:700]
            )
        )

    # -----------------------------------------------------
    # EMPTY
    # -----------------------------------------------------

    if not parts:

        return None

    caption = "\n\n".join(
        parts
    )

    # Telegram caption safety.
    return caption[:1000]


# =========================================================
# SAFE DELETE MESSAGE
# =========================================================

def safe_delete_message(
    chat_id,
    message_id,
):

    if not message_id:

        return

    try:

        delete_message(
            TELEGRAM_API,
            chat_id,
            message_id,
        )

    except Exception as error:

        print(
            "DELETE MESSAGE ERROR:",
            repr(error),
        )


# =========================================================
# DOWNLOAD
# =========================================================

def process_download(
    chat_id,
    url,
):
    """
    Main Instagram download pipeline.

    IMPORTANT FOR VERCEL:
    This function is intentionally NOT launched inside
    a daemon/background thread.

    The webhook request stays alive while this function runs.
    This avoids Vercel killing a background thread after
    returning HTTP 200.
    """

    loading_id = None

    temp_dir = None

    try:

        print(
            "DOWNLOAD REQUEST:",
            chat_id,
            url,
        )

        # =================================================
        # LOADING MESSAGE
        # =================================================

        try:

            loading_id = send_message(
                chat_id,

                "⏳ <b>Fetching Instagram media...</b>\n\n"
                "Please wait.",

                None,

                auto_delete=False,
            )

        except Exception as error:

            print(
                "LOADING MESSAGE ERROR:",
                repr(error),
            )

        # =================================================
        # COOLDOWN
        # =================================================

        wait_for_instagram()

        # =================================================
        # METADATA
        # =================================================

        metadata = {}

        try:

            metadata = (
                get_instagram_metadata(
                    url
                )
                or {}
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

            metadata = {}

        # =================================================
        # DOWNLOAD
        # =================================================

        print(
            "STARTING INSTAGRAM DOWNLOAD:",
            url,
        )

        result = download_instagram_media(
            url
        )

        if not result:

            raise RuntimeError(
                "Downloader returned no result."
            )

        temp_dir, files = result

        print(
            "DOWNLOADED FILES:",
            files,
        )

        # =================================================
        # VALIDATE
        # =================================================

        if not files:

            raise RuntimeError(
                "No media files were downloaded."
            )

        # =================================================
        # REMOVE LOADING
        # =================================================

        if loading_id:

            safe_delete_message(
                chat_id,
                loading_id,
            )

            loading_id = None

        # =================================================
        # CAPTION
        # =================================================

        caption = (
            build_metadata_caption(
                metadata
            )
        )

        # =================================================
        # SEND MEDIA
        # =================================================

        sent = 0

        total_files = len(
            files
        )

        for index, filepath in enumerate(
            files
        ):

            if not filepath:

                continue

            if not os.path.isfile(
                filepath
            ):

                print(
                    "FILE DOES NOT EXIST:",
                    filepath,
                )

                continue

            try:

                current_caption = None

                # Caption only on first file.
                if index == 0:

                    current_caption = caption

                print(
                    "SENDING MEDIA:",
                    filepath,
                )

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

                try:

                    send_message(
                        chat_id,

                        "⚠️ One media file "
                        "could not be sent.",

                        None,
                    )

                except Exception as message_error:

                    print(
                        "MEDIA ERROR MESSAGE FAILED:",
                        repr(message_error),
                    )

        # =================================================
        # NOTHING SENT
        # =================================================

        if sent == 0:

            raise RuntimeError(
                "Downloaded media could not "
                "be sent to Telegram."
            )

        # =================================================
        # RECORD DOWNLOAD
        # =================================================

        record_download(
            chat_id
        )

        # =================================================
        # SUCCESS
        # =================================================

        if total_files > 1:

            send_message(
                chat_id,

                "✅ <b>Done!</b>\n\n"
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

        print(
            "DOWNLOAD SUCCESS:",
            chat_id,
            sent,
        )

    # =====================================================
    # DOWNLOAD ERROR
    # =====================================================

    except Exception as error:

        print(
            "DOWNLOAD ERROR:",
            repr(error),
        )

        # -------------------------------------------------
        # Remove loading
        # -------------------------------------------------

        if loading_id:

            safe_delete_message(
                chat_id,
                loading_id,
            )

            loading_id = None

        # -------------------------------------------------
        # Failure message
        # -------------------------------------------------

        try:

            send_message(
                chat_id,

                "😬 <b>Download failed.</b>\n\n"

                "Make sure the Instagram post is "
                "public and the link is valid.\n\n"

                "🔄 Please try again.",

                None,
            )

        except Exception as message_error:

            print(
                "FAILURE MESSAGE ERROR:",
                repr(message_error),
            )

    # =====================================================
    # CLEANUP
    # =====================================================

    finally:

        if temp_dir:

            try:

                cleanup_media(
                    temp_dir
                )

                print(
                    "TEMP CLEANUP COMPLETE:",
                    temp_dir,
                )

            except Exception as cleanup_error:

                print(
                    "TEMP CLEANUP ERROR:",
                    repr(cleanup_error),
                )


# =========================================================
# BUTTON HANDLER
# =========================================================

def handle_button(
    chat_id,
    callback_id,
    action,
):

    # Always acknowledge button first.
    answer_callback(
        callback_id
    )

    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    if action == "help":

        try:

            send_help(
                chat_id
            )

        except Exception as error:

            print(
                "HELP ERROR:",
                repr(error),
            )

        return

    # -----------------------------------------------------
    # ABOUT
    # -----------------------------------------------------

    if action == "about":

        try:

            send_about(
                chat_id
            )

        except Exception as error:

            print(
                "ABOUT ERROR:",
                repr(error),
            )

        return

    # -----------------------------------------------------
    # MEDIA MODES
    # -----------------------------------------------------

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

        try:

            send_message(
                chat_id,
                messages[action],
                main_keyboard(),
            )

        except Exception as error:

            print(
                "BUTTON MESSAGE ERROR:",
                repr(error),
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
                "commands": json.dumps(
                    commands,
                    ensure_ascii=False,
                )
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

    print(
        "WEBHOOK RECEIVED"
    )

    # =====================================================
    # PARSE UPDATE
    # =====================================================

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    if not data:

        print(
            "EMPTY WEBHOOK UPDATE"
        )

        return "OK", 200

    # =====================================================
    # CALLBACK QUERY
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
            "",
        )

        message = callback.get(
            "message"
        )

        if message:

            chat = message.get(
                "chat"
            )

            if chat:

                try:

                    handle_button(
                        chat["id"],
                        callback_id,
                        callback_data,
                    )

                except Exception as error:

                    print(
                        "CALLBACK HANDLER ERROR:",
                        repr(error),
                    )

        return "OK", 200

    # =====================================================
    # MESSAGE
    # =====================================================

    message = data.get(
        "message"
    )

    if not message:

        return "OK", 200

    # =====================================================
    # CHAT
    # =====================================================

    chat = message.get(
        "chat"
    )

    if not chat:

        return "OK", 200

    chat_id = chat.get(
        "id"
    )

    if not chat_id:

        return "OK", 200

    # =====================================================
    # TEXT
    # =====================================================

    text = (
        message.get(
            "text",
            "",
        )
        or ""
    ).strip()

    if not text:

        return "OK", 200

    print(
        "MESSAGE:",
        chat_id,
        text,
    )

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

        try:

            send_start(
                chat_id
            )

        except Exception as error:

            print(
                "START ERROR:",
                repr(error),
            )

        return "OK", 200

    # =====================================================
    # /HELP
    # =====================================================

    if command == "/help":

        try:

            send_help(
                chat_id
            )

        except Exception as error:

            print(
                "HELP ERROR:",
                repr(error),
            )

        return "OK", 200

    # =====================================================
    # /ABOUT
    # =====================================================

    if command == "/about":

        try:

            send_about(
                chat_id
            )

        except Exception as error:

            print(
                "ABOUT ERROR:",
                repr(error),
            )

        return "OK", 200

    # =====================================================
    # /PING
    # =====================================================

    if command == "/ping":

        try:

            send_ping(
                chat_id
            )

        except Exception as error:

            print(
                "PING ERROR:",
                repr(error),
            )

        return "OK", 200

    # =====================================================
    # /STATS
    # =====================================================

    if command == "/stats":

        try:

            send_stats(
                chat_id
            )

        except Exception as error:

            print(
                "STATS ERROR:",
                repr(error),
            )

        return "OK", 200

    # =====================================================
    # /DOWNLOAD
    # =====================================================

    if command == "/download":

        try:

            send_message(
                chat_id,

                "📥 <b>Send me a public "
                "Instagram link.</b>",

                None,
            )

        except Exception as error:

            print(
                "DOWNLOAD COMMAND ERROR:",
                repr(error),
            )

        return "OK", 200

    # =====================================================
    # INSTAGRAM URL
    # =====================================================

    if is_instagram_url(text):

        print(
            "INSTAGRAM URL DETECTED:",
            text,
        )

        # -------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT use:
        #
        # threading.Thread(...).start()
        #
        # here.
        #
        # Vercel can terminate the invocation after the
        # response is returned, killing the background work.
        #
        # We process it directly.
        # -------------------------------------------------

        process_download(
            chat_id,
            text,
        )

        return "OK", 200

    # =====================================================
    # UNKNOWN TEXT
    # =====================================================

    try:

        send_message(
            chat_id,

            "📥 Send a public Instagram link "
            "to start downloading.",

            main_keyboard(),
        )

    except Exception as error:

        print(
            "UNKNOWN TEXT ERROR:",
            repr(error),
        )

    return "OK", 200


# =========================================================
# STARTUP
# =========================================================

try:

    setup_commands()

except Exception as error:

    print(
        "STARTUP COMMAND ERROR:",
        repr(error),
    )


# =========================================================
# LOCAL SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
    )
