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
    Main downloader.

    Primary:
        parth-dl

    Fallback:
        yt-dlp

    Also returns:
        metadata
    """

    metadata = {
        "title": "",
        "description": "",
    }

    # =============================================
    # METADATA
    # =============================================

    try:

        print(
            "METADATA: fetching..."
        )

        result = get_instagram_metadata(
            url
        )

        if isinstance(
            result,
            dict
        ):

            metadata = {
                "title": (
                    result.get(
                        "title",
                        ""
                    ) or ""
                ).strip(),

                "description": (
                    result.get(
                        "description",
                        ""
                    ) or ""
                ).strip(),
            }

        print(
            "METADATA:",
            metadata,
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
        # PRIMARY: PARTH-DL
        # =============================================

        try:

            print(
                "PARTH_DL: starting..."
            )

            extractor_dir, files = (
                extract_instagram_media(
                    url
                )
            )

            if files:

                print(
                    "PARTH_DL SUCCESS:",
                    files,
                )

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
        # FALLBACK: YT-DLP
        # =============================================

        wait_for_instagram()

        print(
            "YTDLP: starting fallback..."
        )

        ytdlp_dir, files = (
            download_with_ytdlp(
                url
            )
        )

        print(
            "YTDLP SUCCESS:",
            files,
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
