import os

import requests

from config import (
    TELEGRAM_API,
    MAX_FILE_SIZE,
)


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
}


def get_media_type(filepath):

    extension = os.path.splitext(
        filepath
    )[1].lower()

    if extension in IMAGE_EXTENSIONS:

        return (
            "sendPhoto",
            "photo",
        )

    if extension in VIDEO_EXTENSIONS:

        return (
            "sendVideo",
            "video",
        )

    return (
        "sendDocument",
        "document",
    )


def send_media(
    chat_id,
    filepath,
    caption=None,
):

    if not os.path.isfile(filepath):

        raise FileNotFoundError(
            filepath
        )

    filesize = os.path.getsize(
        filepath
    )

    if filesize > MAX_FILE_SIZE:

        raise RuntimeError(
            "File is too large for Telegram bot upload."
        )

    method, field = get_media_type(
        filepath
    )

    data = {
        "chat_id": chat_id,
    }

    if caption:

        data["caption"] = caption

        data["parse_mode"] = "HTML"

    if method == "sendVideo":

        data["supports_streaming"] = True

    with open(
        filepath,
        "rb"
    ) as media:

        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            data=data,
            files={
                field: media,
            },
            timeout=120,
        )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):

        raise RuntimeError(
            result.get(
                "description",
                "Telegram upload failed."
            )
        )

    return result["result"]
