import os
import shutil
import threading
import time

from flask import Flask, request

from config import (
    TELEGRAM_API,
    OWNER_CHAT_ID,
    MAX_CONCURRENT_DOWNLOADS,
)

from telegram import (
    send_message,
    delete_message,
    answer_callback,
    send_media_file,
)

from commands import (
    handle_command,
    handle_button,
)

from downloader import (
    download_instagram,
)


# =========================================================
# APP
# =========================================================

app = Flask(__name__)


# =========================================================
# DOWNLOAD LIMIT
# =========================================================

download_semaphore = threading.Semaphore(
    MAX_CONCURRENT_DOWNLOADS
)


# =========================================================
# TELEGRAM COMMANDS
# =========================================================

# IMPORTANT:
# Commands are NOT registered here.
#
# Add commands from BotFather.
#
# Current commands:
#
# /start
# /download
# /help
# /about
# /ping
#
# Telegram command list is controlled by BotFather.


# =========================================================
# INSTAGRAM URL CHECK
# =========================================================

def is_instagram_url(url):

    if not url:
        return False

    url = url.lower()

    return (
        "instagram.com/" in url
        or "instagr.am/" in url
    )


# =========================================================
# SUCCESS MESSAGE
# =========================================================

def send_success(
    chat_id,
    sent,
    metadata,
):

    title = (
        metadata.get("title")
        or ""
    ).strip()

    description = (
        metadata.get("description")
        or ""
    ).strip()

    text = (
        "🎉 *Download Complete!*\n\n"
        f"📦 Media: `{sent}`"
    )

    if title:

        # Keep Telegram message manageable.
        safe_title = title[:500]

        text += (
            "\n\n🏷️ *Title*\n"
            f"{safe_title}"
        )

    if description:

        safe_description = (
            description[:1500]
        )

        text += (
            "\n\n📝 *Description*\n"
            f"{safe_description}"
        )

    text += "\n\n❤️ Enjoy!"

    send_message(
        chat_id,
        text,
        None,
        "Markdown",
    )


# =========================================================
# DOWNLOAD HANDLER
# =========================================================

def process_download(
    chat_id,
    url,
):

    loading_message_id = None

    temp_dir = None

    try:

        # -------------------------------------------------
        # LOADING
        # -------------------------------------------------

        loading_message_id = send_message(
            chat_id,

            "🔗 *Link received!*\n\n"
            "🔍 Checking Instagram...\n"
            "⚙️ Preparing media...\n\n"
            "⏳ Please wait...",

            None,
            "Markdown",
        )

        # -------------------------------------------------
        # DOWNLOAD
        # -------------------------------------------------

        temp_dir, files, metadata = (
            download_instagram(url)
        )

        if not files:

            raise RuntimeError(
                "No media was downloaded."
            )

        # -------------------------------------------------
        # REMOVE LOADING
        # -------------------------------------------------

        if loading_message_id:

            delete_message(
                chat_id,
                loading_message_id,
            )

            loading_message_id = None

        # -------------------------------------------------
        # SENDING
        # -------------------------------------------------

        sending_message_id = send_message(
            chat_id,

            "📤 *Sending media...*",

            None,
            "Markdown",
        )

        sent = 0

        for filepath in files:

            try:

                send_media_file(
                    chat_id,
                    filepath,
                )

                sent += 1

            except Exception as error:

                print(
                    "MEDIA SEND ERROR:",
                    repr(error),
                )

        # -------------------------------------------------
        # REMOVE SENDING MESSAGE
        # -------------------------------------------------

        delete_message(
            chat_id,
            sending_message_id,
        )

        # -------------------------------------------------
        # NOTHING SENT
        # -------------------------------------------------

        if sent == 0:

            raise RuntimeError(
                "Media download ho gayi, "
                "lekin Telegram par send nahi ho saki."
            )

        # -------------------------------------------------
        # SUCCESS + METADATA
        # -------------------------------------------------

        send_success(
            chat_id,
            sent,
            metadata,
        )

    except Exception as error:

        print(
            "DOWNLOAD ERROR:",
            repr(error),
        )

        if loading_message_id:

            delete_message(
                chat_id,
                loading_message_id,
            )

        error_text = str(error)

        if isinstance(
            error,
            RuntimeError,
        ):

            send_message(
                chat_id,

                f"❌ *{error_text}*",

                None,
                "Markdown",
            )

        else:

            send_message(
                chat_id,

                "😬 *Instagram ne problem "
                "dikha di.*\n\n"
                "🔄 Please try again.",

                None,
                "Markdown",
            )

    finally:

        # -------------------------------------------------
        # CLEANUP
        # -------------------------------------------------

        if temp_dir:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
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
    # CALLBACK BUTTON
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

        answer_callback(
            callback_id
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
                    callback_data,
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

    if not chat:

        return "OK"

    chat_id = chat.get(
        "id"
    )

    text = (
        message.get(
            "text",
            "",
        )
        or ""
        .strip()
    )

    user = (
        message.get(
            "from",
            {},
        )
    )


    # =====================================================
    # COMMAND
    # =====================================================

    if text.startswith("/"):

        handled = handle_command(
            chat_id,
            text,
            user,
        )

        if handled:

            return "OK"


    # =====================================================
    # INSTAGRAM LINK
    # =====================================================

    if not is_instagram_url(text):

        send_message(
            chat_id,

            "🤔 Hmm... mujhe ye samajh nahi aaya.\n\n"
            "🔗 Instagram link bhejo,\n"
            "ya /help use karo. 😎",
        )

        return "OK"


    # =====================================================
    # CONCURRENCY
    # =====================================================

    if not download_semaphore.acquire(
        blocking=False
    ):

        send_message(
            chat_id,

            "⏳ *Thoda busy hoon abhi!*\n\n"
            "Ek download already chal raha hai.\n"
            "Please thodi der baad try karo. 🙏",

            None,
            "Markdown",
        )

        return "OK"


    # =====================================================
    # DOWNLOAD THREAD
    # =====================================================

    def worker():

        try:

            process_download(
                chat_id,
                text,
            )

        finally:

            download_semaphore.release()


    thread = threading.Thread(
        target=worker,
        daemon=True,
    )

    thread.start()

    return "OK"


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        )
