import json
import os
import shutil
import subprocess
import tempfile

from config import (
    DOWNLOAD_TIMEOUT,
)


YTDLP_FORMAT = (
    "best[height<=720][filesize<45M]/"
    "best[height<=720]/"
    "best[filesize<45M]/"
    "best"
)


def _run_ytdlp(
    command,
    timeout=DOWNLOAD_TIMEOUT,
):

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return result


def get_instagram_metadata(url):

    """
    Metadata failure NEVER stops downloading.
    """

    command = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--no-playlist",
        url,
    ]

    try:

        result = _run_ytdlp(
            command,
            timeout=60,
        )

        if result.returncode != 0:

            print(
                "METADATA ERROR:",
                result.stderr[-1000:],
            )

            return {
                "title": "",
                "description": "",
                "uploader": "",
            }

        data = json.loads(
            result.stdout
        )

        return {
            "title": str(
                data.get("title") or ""
            ).strip(),

            "description": str(
                data.get("description") or ""
            ).strip(),

            "uploader": str(
                data.get("uploader")
                or data.get("channel")
                or ""
            ).strip(),
        }

    except Exception as error:

        print(
            "METADATA EXCEPTION:",
            repr(error),
        )

        return {
            "title": "",
            "description": "",
            "uploader": "",
        }


def download_instagram_media(url):

    """
    Download public Instagram media.

    Returns:

        temp_dir,
        files
    """

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_"
    )

    output = os.path.join(
        temp_dir,
        "%(playlist_index|1)s_%(id)s.%(ext)s",
    )

    command = [
        "yt-dlp",

        "--no-warnings",

        "--restrict-filenames",

        # Allows carousel posts.
        "--yes-playlist",

        "-f",
        YTDLP_FORMAT,

        "-o",
        output,

        url,
    ]

    print(
        "YTDLP:",
        " ".join(command),
    )

    try:

        result = _run_ytdlp(
            command
        )

        print(
            "YTDLP RETURN CODE:",
            result.returncode,
        )

        if result.stderr:

            print(
                "YTDLP STDERR:",
                result.stderr[-3000:],
            )

        if result.returncode != 0:

            raise RuntimeError(
                result.stderr[-1500:]
                or "yt-dlp download failed."
            )

        files = []

        for filename in sorted(
            os.listdir(temp_dir)
        ):

            path = os.path.join(
                temp_dir,
                filename
            )

            if os.path.isfile(path):

                files.append(path)

        if not files:

            raise RuntimeError(
                "No media file was created."
            )

        print(
            "YTDLP FILES:",
            files,
        )

        return (
            temp_dir,
            files,
        )

    except Exception:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        raise


def cleanup_media(
    temp_dir
):

    if temp_dir:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
    )
