import os


BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    ""
)

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)

OWNER_CHAT_ID = str(
    os.environ.get(
        "OWNER_CHAT_ID",
        "-1002562168076"
    )
)

MAX_CONCURRENT_DOWNLOADS = 1

INSTAGRAM_COOLDOWN_SECONDS = 15

DOWNLOAD_TIMEOUT = 180

TELEGRAM_TIMEOUT = 120
