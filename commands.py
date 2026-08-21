from config import OWNER_CHAT_ID

from ping import handle_ping

from telegram import (
    send_message,
)


def send_menu(chat_id):

    keyboard = {
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
            ],
        ]
    }

    send_message(
        chat_id,
        "📥 *Instagram Downloader*\n\n"
        "Send any public Instagram link "
        "and I'll handle the rest. 🚀",
        keyboard,
        "Markdown",
    )


def send_help(chat_id):

    send_message(
        chat_id,
        "❓ *How to use Instagram Downloader*\n\n"
        "1️⃣ Copy a public Instagram link.\n"
        "2️⃣ Send it to the bot.\n"
        "3️⃣ Wait for your media. 🚀\n\n"
        "✅ Reels\n"
        "✅ Videos\n"
        "✅ Photos\n"
        "✅ Carousels\n\n"
        "🔒 Private/login-protected posts "
        "aren't supported.",
        None,
        "Markdown",
    )


def send_about(chat_id):

    send_message(
        chat_id,
        "ℹ️ *Instagram All-in-One*\n\n"
        "A Telegram downloader for public "
        "Instagram media. 🚀\n\n"
        "🎬 Reels\n"
        "🎥 Videos\n"
        "🖼️ Photos\n"
        "📚 Carousels",
        None,
        "Markdown",
    )


def handle_command(
    chat_id,
    text,
    user,
):

    if not text:
        return False

    cmd = (
        text.split()[0]
        .lower()
        .split("@")[0]
    )

    if cmd == "/start":
        send_menu(chat_id)
        return True

    if cmd == "/help":
        send_help(chat_id)
        return True

    if cmd == "/about":
        send_about(chat_id)
        return True

    if cmd == "/download":

        send_message(
            chat_id,
            "📥 *Ready!*\n\n"
            "Send a public Instagram "
            "Reel, Video, Photo or "
            "Carousel link. 🚀",
            None,
            "Markdown",
        )

        return True

    if cmd == "/ping":

        result = handle_ping(
            chat_id,
            user,
        )

        send_message(
            chat_id,
            result,
            None,
            "Markdown",
        )

        return True

    return False


def handle_button(
    chat_id,
    action,
):

    if action == "menu":
        send_menu(chat_id)

    elif action == "help":
        send_help(chat_id)

    elif action == "reels":

        send_message(
            chat_id,
            "🎬 *Reels mode ready!*\n\n"
            "Send a public Instagram Reel link.",
            None,
            "Markdown",
        )

    elif action == "videos":

        send_message(
            chat_id,
            "🎥 *Video mode ready!*\n\n"
            "Send a public Instagram video link.",
            None,
            "Markdown",
        )

    elif action == "photos":

        send_message(
            chat_id,
            "🖼️ *Photos mode ready!*\n\n"
            "Send a public Instagram photo link.",
            None,
            "Markdown",
        )

    elif action == "carousel":

        send_message(
            chat_id,
            "📚 *Carousel mode ready!*\n\n"
            "Send a public Instagram carousel link.",
            None,
            "Markdown",
        )
