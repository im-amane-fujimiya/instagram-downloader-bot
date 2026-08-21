import os
import time
from datetime import datetime, timezone


OWNER_CHAT_ID = str(
    os.environ.get(
        "OWNER_CHAT_ID",
        "-1002562168076"
    )
)


def handle_ping(chat_id, user):
    """
    Owner-only /ping command.

    Returns:
    - detailed bot information for owner
    - simple status for everyone else
    """

    chat_id = str(chat_id)

    if chat_id != OWNER_CHAT_ID:
        return (
            "🏓 *Pong!*\n\n"
            "🤖 Bot is online."
        )

    first_name = (
        user.get("first_name")
        or "Unknown"
    )

    last_name = (
        user.get("last_name")
        or ""
    )

    username = (
        user.get("username")
        or "No username"
    )

    user_id = user.get(
        "id",
        "Unknown"
    )

    full_name = (
        f"{first_name} {last_name}"
    ).strip()

    now = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    return (
        "🏓 *PONG — BOT ONLINE*\n\n"
        "🤖 Status: `ONLINE`\n"
        f"🕐 Server time: `{now}`\n\n"
        "👤 *User Information*\n"
        f"• Name: `{full_name}`\n"
        f"• Username: `@{username}`\n"
        f"• User ID: `{user_id}`\n"
        f"• Chat ID: `{chat_id}`\n\n"
        "⚙️ *Bot Information*\n"
        f"• Owner ID: `{OWNER_CHAT_ID}`\n"
        "• Instagram Downloader: `ACTIVE`\n"
        "• Webhook: `ACTIVE`\n"
        "• Server: `RENDER`\n"
    )
