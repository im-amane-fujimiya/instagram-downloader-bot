import os
import time

START_TIME = time.time()


def get_ping_info(chat_id, total_downloads=0, user_downloads=0):
    uptime = int(time.time() - START_TIME)

    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60
    seconds = uptime % 60

    username = os.environ.get("BOT_USERNAME", "Not set")

    return (
        "🏓 PONG!\n\n"
        f"🆔 Your ID: `{chat_id}`\n"
        f"🤖 Bot: @{username}\n\n"
        "📊 DOWNLOADS\n"
        f"🌍 Total: {total_downloads}\n"
        f"👤 Yours: {user_downloads}\n\n"
        "⏱️ Uptime\n"
        f"{days}d {hours}h {minutes}m {seconds}s\n\n"
        "🟢 Server: Online\n"
        "🟢 Bot: Running"
    )
