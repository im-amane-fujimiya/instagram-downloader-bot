import os
import requests

from database import (
    get_active_chats,
    deactivate_chat,
)


BOT_TOKEN = os.environ["BOT_TOKEN"]

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)


def telegram_request(
    method,
    data=None,
    files=None
):

    url = f"{TELEGRAM_API}/{method}"

    response = requests.post(
        url,
        data=data,
        files=files,
        timeout=60
    )

    try:
        return response.json()
    except Exception:
        return {
            "ok": False,
            "description": response.text
        }


def send_text(
    chat_id,
    text
):

    return telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


def copy_message(
    target_chat_id,
    from_chat_id,
    message_id
):

    return telegram_request(
        "copyMessage",
        {
            "chat_id": target_chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id
        }
    )


def broadcast_message(
    source_chat_id,
    message_id
):

    chats = get_active_chats()

    total = len(chats)
    success = 0
    failed = 0

    for chat in chats:

        target_chat_id = chat["chat_id"]

        result = copy_message(
            target_chat_id,
            source_chat_id,
            message_id
        )

        if result.get("ok"):

            success += 1

        else:

            failed += 1

            error_code = result.get(
                "error_code"
            )

            description = str(
                result.get(
                    "description",
                    ""
                )
            ).lower()

            # Bot removed / chat unavailable
            if error_code in (
                400,
                403
            ):

                if (
                    "chat not found"
                    in description
                    or
                    "bot was kicked"
                    in description
                    or
                    "forbidden"
                    in description
                    or
                    "not enough rights"
                    in description
                ):

                    deactivate_chat(
                        target_chat_id
                    )

    return {
        "total": total,
        "success": success,
        "failed": failed
  }
