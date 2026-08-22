import threading
import requests

from config import (
    DELETE_AFTER,
)


def delete_message(
    telegram_api,
    chat_id,
    message_id
):

    try:

        response = requests.post(
            f"{telegram_api}/deleteMessage",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
            },
            timeout=20,
        )

        if not response.ok:

            print(
                "DELETE ERROR:",
                response.text,
            )

    except Exception as error:

        print(
            "DELETE EXCEPTION:",
            repr(error),
        )


def schedule_delete(
    telegram_api,
    chat_id,
    message_id,
    delay=DELETE_AFTER,
):

    def worker():

        delete_message(
            telegram_api,
            chat_id,
            message_id,
        )

    timer = threading.Timer(
        delay,
        worker,
    )

    timer.daemon = True
    timer.start()

    return timer
