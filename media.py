import os
import tempfile
import requests

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def download_file(url):
    """
    Download a publicly accessible direct media URL
    into a temporary file.
    """
    response = requests.get(
        url,
        stream=True,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    )

    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()

    if "image" in content_type:
        extension = ".jpg"
    elif "video" in content_type:
        extension = ".mp4"
    else:
        extension = ".bin"

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension
    )

    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if chunk:
                temp.write(chunk)

        temp.close()
        return temp.name

    except Exception:
        temp.close()
        try:
            os.remove(temp.name)
        except OSError:
            pass
        raise


def send_photo(chat_id, filepath):
    with open(filepath, "rb") as photo:
        response = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": photo},
            timeout=120
        )
    response.raise_for_status()


def send_video(chat_id, filepath):
    with open(filepath, "rb") as video:
        response = requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={"chat_id": chat_id},
            files={"video": video},
            timeout=120
        )
    response.raise_for_status()


def send_media(chat_id, filepath):
    extension = os.path.splitext(filepath)[1].lower()

    if extension in (".jpg", ".jpeg", ".png", ".webp"):
        send_photo(chat_id, filepath)
    elif extension in (".mp4", ".mov", ".webm", ".mkv"):
        send_video(chat_id, filepath)
    else:
        raise ValueError(f"Unsupported media type: {extension}")


def process_media_urls(chat_id, media_urls):
    """
    Send multiple direct media URLs one-by-one.
    """
    sent = 0

    for url in media_urls:
        filepath = None
        try:
            filepath = download_file(url)
            send_media(chat_id, filepath)
            sent += 1
        except Exception as error:
            print(f"FAILED TO PROCESS URL {url}: {repr(error)}")
        finally:
            if filepath:
                try:
                    os.remove(filepath)
                except OSError:
                    pass

    return sent
        
