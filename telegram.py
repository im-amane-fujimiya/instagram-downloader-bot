import requests

from config import (
    TELEGRAM_API,
    TELEGRAM_TIMEOUT,
)

from cleanup import schedule_delete


def send_message(
    chat_id,
    text,
    reply_markup=None,
    parse_mode=None,
):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    if parse_mode:
        data["parse_mode"] = parse_mode

    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=data,
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    message_id = (
        result["result"]["message_id"]
    )

    schedule_delete(
        TELEGRAM_API,
        chat_id,
        message_id,
    )

    return message_id


def delete_message(
    chat_id,
    message_id,
):
    try:
        response = requests.post(
            f"{TELEGRAM_API}/deleteMessage",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
            },
            timeout=30,
        )

        if not response.ok:
            print(
                "DELETE MESSAGE ERROR:",
                response.text,
            )

    except Exception as error:
        print(
            "DELETE MESSAGE ERROR:",
            repr(error),
        )


def answer_callback(
    callback_id,
):
    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={
                "callback_query_id":
                    callback_id
            },
            timeout=30,
        )

    except Exception as error:
        print(
            "CALLBACK ERROR:",
            repr(error),
        )


def send_media_file(
    chat_id,
    filepath,
):
    import os

    extension = os.path.splitext(
        filepath
    )[1].lower()

    if extension in (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    ):
        method = "sendPhoto"
        field = "photo"

    elif extension in (
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
    ):
        method = "sendVideo"
        field = "video"

    else:
        method = "sendDocument"
        field = "document"

    with open(
        filepath,
        "rb",
    ) as media:

        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            data={
                "chat_id": chat_id
            },
            files={
                field: media
            },
            timeout=TELEGRAM_TIMEOUT,
        )

    response.raise_for_status()
