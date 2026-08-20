import threading
import requests

DELETE_AFTER = 3 * 60 * 60


def schedule_delete(
    telegram_api,
    chat_id,
    message_id
):

    def delete():

        try:

            response = requests.post(
                f"{telegram_api}/deleteMessage",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id
                },
                timeout=30
            )

            if not response.ok:
                print(
                    "AUTO DELETE ERROR:",
                    response.text
                )

        except Exception as error:
            print(
                "AUTO DELETE ERROR:",
                repr(error)
            )

    timer = threading.Timer(
        DELETE_AFTER,
        delete
    )

    timer.daemon = True
    timer.start()
