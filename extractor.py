import json
import os
import shutil
import subprocess
import tempfile

from config import DOWNLOAD_TIMEOUT


YTDLP_FORMAT = (
    "best[height<=720][filesize<45M]/"
    "best[height<=720]/"
    "best[filesize<45M]/"
    "best"
)


def _run_ytdlp(command, timeout=DOWNLOAD_TIMEOUT):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _empty_metadata():
    return {
        "title": "",
        "description": "",
        "uploader": "",
    }


def _clean_url(url):
    """
    Remove Instagram tracking parameters.
    Keeps the actual post/reel URL.
    """
    url = (url or "").strip()

    if "?" in url:
        url = url.split("?", 1)[0]

    return url.rstrip("/")


# =========================================================
# PARTH-DL IMPORT
# =========================================================

def _get_parth():
    try:
        import parth_dl
        return parth_dl
    except Exception as error:
        print(
            "PARTH-DL IMPORT FAILED:",
            repr(error),
        )
        return None


# =========================================================
# PARTH-DL INFO
# =========================================================

def _parth_metadata(url):
    parth = _get_parth()

    if not parth:
        return _empty_metadata()

    try:
        info = parth.get_info(
            _clean_url(url)
        )

        if not isinstance(info, dict):
            return _empty_metadata()

        return {
            "title": str(
                info.get("title")
                or info.get("caption")
                or ""
            ).strip(),

            "description": str(
                info.get("description")
                or info.get("caption")
                or ""
            ).strip(),

            "uploader": str(
                info.get("username")
                or info.get("uploader")
                or info.get("owner_username")
                or ""
            ).strip(),
        }

    except Exception as error:
        print(
            "PARTH METADATA FAILED:",
            repr(error),
        )

        return _empty_metadata()


# =========================================================
# YT-DLP METADATA
# =========================================================

def _ytdlp_metadata(url):
    command = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--no-playlist",
        "--flat-playlist",
        _clean_url(url),
    ]

    try:
        result = _run_ytdlp(
            command,
            timeout=60,
        )

        if result.returncode != 0:
            print(
                "METADATA YTDLP ERROR:",
                result.stderr[-1500:],
            )

            return _empty_metadata()

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
            "YTDLP METADATA EXCEPTION:",
            repr(error),
        )

        return _empty_metadata()


# =========================================================
# METADATA
# =========================================================

def get_instagram_metadata(url):
    """
    Metadata order:

        1. parth-dl
        2. yt-dlp

    Metadata failure never blocks downloading.
    """

    metadata = _parth_metadata(url)

    if any(
        metadata.get(key)
        for key in (
            "title",
            "description",
            "uploader",
        )
    ):
        print(
            "METADATA SOURCE: parth-dl"
        )

        return metadata

    metadata = _ytdlp_metadata(url)

    if any(
        metadata.get(key)
        for key in (
            "title",
            "description",
            "uploader",
        )
    ):
        print(
            "METADATA SOURCE: yt-dlp"
        )

    return metadata


# =========================================================
# COLLECT FILES
# =========================================================

def _collect_files(temp_dir):
    files = []

    if not os.path.isdir(temp_dir):
        return files

    for root, dirs, filenames in os.walk(
        temp_dir
    ):
        dirs.sort()
        filenames.sort()

        for filename in filenames:

            path = os.path.join(
                root,
                filename,
            )

            if os.path.isfile(path):
                files.append(path)

    return files


# =========================================================
# PARTH-DL DOWNLOAD
# =========================================================

def _download_with_parth(url, temp_dir):
    """
    Primary downloader.

    parth-dl is preferred because it was
    previously working well for photos/carousels.
    """

    parth = _get_parth()

    if not parth:
        raise RuntimeError(
            "parth-dl is not installed."
        )

    clean_url = _clean_url(url)

    print(
        "PARTH-DL:",
        clean_url,
    )

    result = parth.download(
        clean_url,
        output_dir=temp_dir,
    )

    print(
        "PARTH RESULT:",
        repr(result),
    )

    files = _collect_files(
        temp_dir
    )

    if not files:
        raise RuntimeError(
            "parth-dl completed but "
            "no media file was created."
        )

    print(
        "PARTH FILES:",
        files,
    )

    return files


# =========================================================
# YT-DLP DOWNLOAD
# =========================================================

def _download_with_ytdlp(url, temp_dir):
    """
    Fallback downloader.

    Primarily useful for Reels/videos.
    """

    output = os.path.join(
        temp_dir,
        "%(playlist_index)s_%(id)s.%(ext)s",
    )

    command = [
        "yt-dlp",

        "--no-warnings",
        "--restrict-filenames",

        "--yes-playlist",

        "-f",
        YTDLP_FORMAT,

        "-o",
        output,

        _clean_url(url),
    ]

    print(
        "YTDLP:",
        " ".join(command),
    )

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
            result.stderr[-4000:],
        )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr[-2000:]
            or "yt-dlp download failed."
        )

    files = _collect_files(
        temp_dir
    )

    if not files:
        raise RuntimeError(
            "yt-dlp completed but "
            "no media file was created."
        )

    print(
        "YTDLP FILES:",
        files,
    )

    return files


# =========================================================
# MAIN DOWNLOAD FUNCTION
# =========================================================

def download_instagram_media(url):
    """
    Public interface used by main.py.

    Order:

        parth-dl
            ↓
        yt-dlp fallback

    Returns:

        temp_dir,
        files
    """

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_"
    )

    # -----------------------------------------------------
    # PRIMARY: PARTH-DL
    # -----------------------------------------------------

    try:

        files = _download_with_parth(
            url,
            temp_dir,
        )

        return (
            temp_dir,
            files,
        )

    except Exception as error:

        print(
            "PARTH-DL FAILED:",
            repr(error),
        )

        # Clean failed attempt.
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        temp_dir = tempfile.mkdtemp(
            prefix="instagram_"
        )

    # -----------------------------------------------------
    # FALLBACK: YT-DLP
    # -----------------------------------------------------

    try:

        files = _download_with_ytdlp(
            url,
            temp_dir,
        )

        return (
            temp_dir,
            files,
        )

    except Exception as error:

        print(
            "YTDLP FAILED:",
            repr(error),
        )

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        raise RuntimeError(
            "Both downloaders failed."
        )


# =========================================================
# CLEANUP
# =========================================================

def cleanup_media(temp_dir):

    if temp_dir:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )
