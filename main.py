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
from broadcast import (
    register_chat,
    unregister_chat,
    get_broadcast_chats,
    broadcast_copy_message,
)


TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# =========================================================
# OWNER CHAT ID
# =========================================================

OWNER_CHAT_ID = "-1002025076123"

app = Flask(__name__)


# =========================================================
# CONCURRENCY LIMIT
# =========================================================

MAX_CONCURRENT_DOWNLOADS = 1

download_semaphore = threading.Semaphore(
    MAX_CONCURRENT_DOWNLOADS
)

PENDING_BROADCAST = set()
BROADCAST_CONFIRMATIONS = {}


# =========================================================
# INSTAGRAM COOLDOWN
# =========================================================

INSTAGRAM_COOLDOWN_SECONDS = 15

_last_instagram_request_lock = threading.Lock()
_last_instagram_request_time = 0.0


def wait_for_instagram_cooldown():

    global _last_instagram_request_time

    with _last_instagram_request_lock:

        now = time.monotonic()

        elapsed = (
            now - _last_instagram_request_time
        )

        remaining = (
            INSTAGRAM_COOLDOWN_SECONDS
            - elapsed
        )

        if remaining > 0:
            time.sleep(remaining)

        _last_instagram_request_time = (
            time.monotonic()
        )


# =========================================================
# STATS
# =========================================================

STATS_FILE = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "stats.json"
)

_stats_lock = threading.Lock()


def _load_stats():

    try:

        with open(
            STATS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {
            "total": 0,
            "users": {}
        }


def record_download(chat_id):

    with _stats_lock:

        stats = _load_stats()

        stats["total"] = (
            stats.get("total", 0) + 1
        )

        users = stats.setdefault(
            "users",
            {}
        )

        key = str(chat_id)

        users[key] = (
            users.get(key, 0) + 1
        )

        try:

            with open(
                STATS_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    stats,
                    f
                )

        except Exception as error:

            print(
                "STATS WRITE ERROR:",
                repr(error)
            )


def get_stats(chat_id):

    with _stats_lock:

        stats = _load_stats()

        total = stats.get(
            "total",
            0
        )

        mine = (
            stats
            .get("users", {})
            .get(str(chat_id), 0)
        )

        return total, mine


# =========================================================
# BANNER
# =========================================================

BANNER_PATH = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "1787159942996.png"
)


# =========================================================
# TELEGRAM COMMANDS + MENU
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
            "command": "stats",
            "description": "See download stats"
        },
        {
            "command": "broadcast",
            "description": "Broadcast to groups/channels"
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


# =========================================================
# SEND MESSAGE
# =========================================================

def telegram_request(
    method,
    payload=None,
    timeout=30
):

    response = requests.post(
        f"{TELEGRAM_API}/{method}",
        json=payload or {},
        timeout=timeout
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):

        raise RuntimeError(
            result.get(
                "description",
                "Telegram API error"
            )
        )

    return result.get("result")


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

        data["reply_markup"] = (
            reply_markup
        )

    if parse_mode:

        data["parse_mode"] = (
            parse_mode
        )

    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=data,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    message_id = (
        result["result"]["message_id"]
    )

    schedule_delete(
        TELEGRAM_API,
        chat_id,
        message_id
    )

    return message_id


# =========================================================
# DELETE MESSAGE
# =========================================================

def delete_message(
    chat_id,
    message_id
):

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


# =========================================================
# ANSWER CALLBACK
# =========================================================

def answer_callback(
    callback_id
):

    if not callback_id:
        return

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

        if os.path.isfile(
            BANNER_PATH
        ):

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

            photo_message_id = (
                response.json()
                ["result"]
                ["message_id"]
            )

            schedule_delete(
                TELEGRAM_API,
                chat_id,
                photo_message_id
            )

        else:

            print(
                "BANNER NOT FOUND:",
                BANNER_PATH
            )

            send_message(
                chat_id,
                caption,
                None,
                "Markdown"
            )

    except Exception as error:

        print(
            "START ERROR:",
            repr(error)
        )

        send_menu(chat_id)


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
                {
                    "text": "📥 Download",
                    "callback_data": "menu"
                },
                {
                    "text": "❓ Help",
                    "callback_data": "help"
                }
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

def send_media(
    chat_id,
    filepath
):

    extension = (
        os.path.splitext(filepath)[1]
        .lower()
    )

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
            "yt-dlp finished but no media file was created."
        )

    return temp_dir, files


# =========================================================
# URL CHECK
# =========================================================

def is_instagram_url(url):

    url = url.strip().lower()

    return (
        "instagram.com/" in url
        or "www.instagram.com/" in url
        or "instagr.am/" in url
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

    if action == "broadcast_cancel":

        BROADCAST_CONFIRMATIONS.pop(
            str(chat_id),
            None
        )

        send_message(
            chat_id,
            "❌ *Broadcast cancelled.*",
            None,
            "Markdown"
        )

        return

    if action == "broadcast_confirm":

        if str(chat_id) != OWNER_CHAT_ID:

            return

        message_id = (
            BROADCAST_CONFIRMATIONS.pop(
                str(chat_id),
                None
            )
        )

        if not message_id:

            send_message(
                chat_id,
                "⚠️ *Broadcast expired.* "
                "Use /broadcast again.",
                None,
                "Markdown"
            )

            return

        targets = get_broadcast_chats()

        send_message(
            chat_id,
            "📢 *Broadcasting...*\n\n"
            f"Targets: {len(targets)}",
            None,
            "Markdown"
        )

        success, failed, total = (
            broadcast_copy_message(
                TELEGRAM_API,
                chat_id,
                message_id,
                telegram_request
            )
        )

        send_message(
            chat_id,
            "📢 *Broadcast complete!*\n\n"
            f"📨 Targets: *{total}*\n"
            f"✅ Sent: *{success}*\n"
            f"❌ Failed: *{failed}*",
            None,
            "Markdown"
        )

        return

    if action == "menu":

        send_menu(chat_id)

    elif action == "help":

        send_help(chat_id)

    elif action == "reels":

        send_message(
            chat_id,
            "🎬 *Reels mode ready!*\n\n"
            "Send a public Instagram Reel link. 🚀",
            None,
            "Markdown"
        )

    elif action == "videos":

        send_message(
            chat_id,
            "🎥 *Video mode ready!*\n\n"
            "Send a public Instagram video post link. 🚀",
            None,
            "Markdown"
        )

    elif action == "photos":

        send_message(
            chat_id,
            "🖼️ *Photos mode ready!*\n\n"
            "Send a public Instagram photo post link. 🚀",
            None,
            "Markdown"
        )

    elif action == "carousel":

        send_message(
            chat_id,
            "📚 *Carousel mode ready!*\n\n"
            "Send a public Instagram carousel link. 🚀",
            None,
            "Markdown"
        )


# =========================================================
# PROCESS TELEGRAM UPDATE
# =========================================================

def process_update():

    data = request.get_json(
        silent=True
    ) or {}

    # =====================================================
    # CHANNEL POSTS
    # =====================================================

    channel_post = data.get(
        "channel_post"
    )

    if channel_post:

        register_chat(
            channel_post.get("chat")
        )

        return "OK"

    # =====================================================
    # BOT CHAT MEMBERSHIP
    # =====================================================

    my_chat_member = data.get(
        "my_chat_member"
    )

    if my_chat_member:

        member_chat = (
            my_chat_member.get("chat")
        )

        status = (
            my_chat_member
            .get("new_chat_member", {})
            .get("status")
        )

        if member_chat:

            if status in (
                "member",
                "administrator"
            ):

                register_chat(
                    member_chat
                )

            elif status in (
                "left",
                "kicked"
            ):

                unregister_chat(
                    member_chat.get("id")
                )

        return "OK"

    # =====================================================
    # INLINE BUTTON
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

    register_chat(
        chat
    )

    # =====================================================
    # PENDING BROADCAST MESSAGE
    # =====================================================

    if str(chat_id) in PENDING_BROADCAST:

        PENDING_BROADCAST.discard(
            str(chat_id)
        )

        if str(chat_id) != OWNER_CHAT_ID:

            return "OK"

        message_id = message.get(
            "message_id"
        )

        if not message_id:

            send_message(
                chat_id,
                "❌ Could not read that message.",
                None,
                "Markdown"
            )

            return "OK"

        BROADCAST_CONFIRMATIONS[
            str(chat_id)
        ] = message_id

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Send Broadcast",
                        "callback_data": "broadcast_confirm"
                    },
                    {
                        "text": "❌ Cancel",
                        "callback_data": "broadcast_cancel"
                    }
                ]
            ]
        }

        send_message(
            chat_id,
            "📢 *Broadcast ready!*\n\n"
            "Ye message registered groups/channels "
            "me copy hoga.\n\n"
            "Neeche *Send Broadcast* dabao.",
            keyboard,
            "Markdown"
        )

        return "OK"

    # =====================================================
    # COMMANDS
    # =====================================================

    if text == "/start":

        send_start(
            chat_id
        )

        return "OK"

    if text == "/help":

        send_help(
            chat_id
        )

        return "OK"

    if text == "/about":

        send_about(
            chat_id
        )

        return "OK"

    if text == "/stats":

        total, mine = get_stats(
            chat_id
        )

        if str(chat_id) == OWNER_CHAT_ID:

            send_message(
                chat_id,
                "📊 *Bot Stats (Owner view)*\n\n"
                f"🌍 Total downloads (all users): {total}\n"
                f"👤 Your downloads: {mine}",
                None,
                "Markdown"
            )

        else:

            send_message(
                chat_id,
                "📊 *Your Stats*\n\n"
                f"👤 Your downloads: {mine}",
                None,
                "Markdown"
            )

        return "OK"

    # =====================================================
    # BROADCAST COMMAND
    # =====================================================

    if (
        text
        and text.split()[0]
        .split("@")[0]
        .lower() == "/broadcast"
    ):

        if str(chat_id) != OWNER_CHAT_ID:

            send_message(
                chat_id,
                "⛔ *Owner only.*",
                None,
                "Markdown"
            )

            return "OK"

        PENDING_BROADCAST.add(
            str(chat_id)
        )

        send_message(
            chat_id,
            "📢 *Broadcast mode ON*\n\n"
            "Ab jo *next message* bhejoge, "
            "usko broadcast ke liye ready karunga.\n\n"
            "Normal messages automatically "
            "broadcast nahi honge.",
            None,
            "Markdown"
        )

        return "OK"

    if text == "/download":

        send_message(
            chat_id,
            "📥 *Ready!*\n\n"
            "Send your public Instagram "
            "Reel, Video, Photo or Carousel link. 🚀",
            None,
            "Markdown"
        )

        return "OK"

    # =====================================================
    # URL VALIDATION
    # =====================================================

    if not is_instagram_url(text):

        send_message(
            chat_id,
            "🤔 Hmm... mujhe ye samajh nahi aaya.\n\n"
            "🔗 Instagram link bhejo, "
            "ya /help use karo. 😎"
        )

        return "OK"

    # =====================================================
    # BUSY CHECK
    # =====================================================

    if not download_semaphore.acquire(
        blocking=False
    ):

        send_message(
            chat_id,
            "⏳ *Thoda busy hoon abhi!*\n\n"
            "Ek aur download chal raha hai. "
            "Please 20-30 second baad try karo. 🙏",
            None,
            "Markdown"
        )

        return "OK"

    try:

        _handle_download(
            chat_id,
            text
        )

    finally:

        download_semaphore.release()

    return "OK"


# =========================================================
# WEBHOOK
# =========================================================

@app.post("/")
def webhook_root():

    return process_update()


@app.post("/webhook")
def webhook():

    return process_update()


# =========================================================
# HOME / HEALTH CHECK
# =========================================================

@app.get("/")
def home_get():

    return (
        "Instagram All-in-One Bot is running!"
    )


# =========================================================
# DOWNLOAD HANDLER
# =========================================================

def _handle_download(
    chat_id,
    text
):

    loading_message_id = None
    sending_message_id = None

    ytdlp_dir = None
    extractor_dir = None

    try:

        loading_message_id = send_message(
            chat_id,
            "🔗 *Link received!*\n\n"
            "🔍 Checking the post...\n"
            "⚙️ Preparing your media...\n\n"
            "⏳ Hang tight, I'm on it 😎",
            None,
            "Markdown"
        )

        # =================================================
        # PRIMARY: YT-DLP
        # =================================================

        wait_for_instagram_cooldown()

        try:

            ytdlp_dir, files = (
                download_with_ytdlp(
                    text
                )
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
            # FALLBACK: EXTRACTOR
            # =============================================

            wait_for_instagram_cooldown()

            extractor_dir, files = (
                extract_instagram_media(
                    text
                )
            )

        # =================================================
        # DELETE LOADING
        # =================================================

        delete_message(
            chat_id,
            loading_message_id
        )

        loading_message_id = None

        # =================================================
        # SEND MEDIA
        # =================================================

        sending_message_id = send_message(
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

        delete_message(
            chat_id,
            sending_message_id
        )

        sending_message_id = None

        if sent == 0:

            raise Exception(
                "No media could be sent to Telegram."
            )

        # =================================================
        # SUCCESS
        # =================================================

        send_message(
            chat_id,
            f"🎉 *Done!*\n\n"
            f"📦 {sent} media file(s) delivered.\n"
            f"❤️ Enjoy!",
            None,
            "Markdown"
        )

        record_download(
            chat_id
        )

    # =====================================================
    # TIMEOUT
    # =====================================================

    except subprocess.TimeoutExpired:

        delete_message(
            chat_id,
            loading_message_id
        )

        delete_message(
            chat_id,
            sending_message_id
        )

        send_message(
            chat_id,
            "⏱️ *Download timed out.*\n\n"
            "Try a smaller public Instagram post. 😅",
            None,
            "Markdown"
        )

    # =====================================================
    # ALL OTHER ERRORS
    # =====================================================

    except Exception as error:

        error_text = str(error)

        print(
            "DOWNLOAD ERROR:",
            repr(error_text)
        )

        delete_message(
            chat_id,
            loading_message_id
        )

        delete_message(
            chat_id,
            sending_message_id
        )

        if isinstance(
            error,
            RuntimeError
        ):

            send_message(
                chat_id,
                f"😬 *{error_text}*",
                None,
                "Markdown"
            )

        else:

            send_message(
                chat_id,
                "😬 *Instagram ne thoda nakhra "
                "dikha diya.*\n\n"
                "🔄 Please try again in a moment.",
                None,
                "Markdown"
            )

    # =====================================================
    # CLEANUP
    # =====================================================

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
