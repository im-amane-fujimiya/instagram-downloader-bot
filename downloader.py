import os
import shutil
import subprocess
import tempfile
import threading
import time

from extractor import (
    extract_instagram_media,
    cleanup_media,
)

from config import (
    INSTAGRAM_COOLDOWN_SECONDS,
    DOWNLOAD_TIMEOUT,
)

from metadata import (
    get_instagram_metadata,
)


_download_lock = threading.Lock()

_last_request_time = 0.0


def wait_for_instagram():
    global _last_request_time

    with _download_lock:

        now = time.monotonic()

        elapsed = (
            now - _last_request_time
        )

        remaining = (
            INSTAGRAM_COOLDOWN_SECONDS
            - elapsed
        )

        if remaining > 0:
            time.sleep(
                remaining
            )

        _last_request_time = (
            time.monotonic()
        )


def download_with_ytdlp(url):

    temp_dir = tempfile.mkdtemp(
        prefix="ytdlp_"
    )

    output = os.path.join(
        temp_dir,
        "%(playlist_index)s_%(id)s.%(ext)s",
    )

    command = [
        "yt-dlp",
        "--no-warnings",
        "--restrict-filenames",
        "--no-playlist",
        "-f",
        (
            "best[height<=720]"
            "[filesize<80M]/"
            "best[height<=720]/"
            "best[filesize<80M]/"
            "best"
        ),
        "-o",
        output,
        url,
    ]

    print(
        "YTDLP:",
        " ".join(command),
    )

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=DOWNLOAD_TIMEOUT,
        )

        print(
            "YTDLP RETURN CODE:",
            result.returncode,
        )

        print(
            "YTDLP STDERR:",
            result.stderr[-2000:],
        )

        if result.returncode != 0:
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
            raise Exception(
                "yt-dlp finished but "
                "no media was created."
            )

        return temp_dir, files

    except Exception:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        raise


def download_instagram(url):

    """
    Returns:

        temp_dir,
        files,
        metadata

    parth_dl is the primary downloader.
    yt-dlp is used as fallback.
    """

    metadata = {
        "title": "",
        "description": "",
    }

    # Metadata must never block download.
    try:
        metadata = (
            get_instagram_metadata(url)
        )

    except Exception as error:
        print(
            "METADATA FAILED:",
            repr(error),
        )

    wait_for_instagram()

    extractor_dir = None
    ytdlp_dir = None

    try:

        # =============================================
        # PRIMARY: parth_dl
        # =============================================

        try:

            extractor_dir, files = (
                extract_instagram_media(
                    url
                )
            )

            if files:
                return (
                    extractor_dir,
                    files,
                    metadata,
                )

        except Exception as error:

            print(
                "PARTH_DL FAILED:",
                repr(error),
            )

        # =============================================
        # FALLBACK: yt-dlp
        # =============================================

        wait_for_instagram()

        ytdlp_dir, files = (
            download_with_ytdlp(
                url
            )
        )

        return (
            ytdlp_dir,
            files,
            metadata,
        )

    except Exception:

        if extractor_dir:
            cleanup_media(
                extractor_dir
            )

        if ytdlp_dir:
            shutil.rmtree(
                ytdlp_dir,
                ignore_errors=True,
            )

        raise
