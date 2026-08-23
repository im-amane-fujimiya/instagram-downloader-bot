import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

from config import DOWNLOAD_TIMEOUT


# =========================================================
# SETTINGS
# =========================================================

YTDLP_FORMAT = (
    "best[height<=720][filesize<45M]/"
    "best[height<=720]/"
    "best[filesize<45M]/"
    "best"
)

REQUEST_TIMEOUT = 60


# =========================================================
# URL CLEANER
# =========================================================

def clean_instagram_url(url):
    """
    Remove Instagram tracking query parameters.
    Keeps the actual Instagram post/reel URL.
    """

    try:
        parts = urlsplit(url)

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path.rstrip("/"),
                "",
                "",
            )
        )

    except Exception:
        return url


# =========================================================
# COMMAND RUNNER
# =========================================================

def _run_ytdlp(
    command,
    timeout=DOWNLOAD_TIMEOUT,
):

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# =========================================================
# METADATA
# =========================================================

def get_instagram_metadata(url):
    """
    Metadata failure NEVER stops downloading.

    Parth-dl is used first because it is already
    working better with current Instagram posts.
    """

    clean_url = clean_instagram_url(url)

    # -----------------------------------------------------
    # PARTH-DL METADATA
    # -----------------------------------------------------

    try:

        import parth_dl

        info = parth_dl.info(
            clean_url
        )

        if isinstance(info, dict):

            print(
                "PARTH INFO:",
                info,
            )

            return {
                "title": str(
                    info.get("title") or ""
                ).strip(),

                "description": str(
                    info.get("description") or ""
                ).strip(),

                "uploader": str(
                    info.get("uploader")
                    or info.get("username")
                    or ""
                ).strip(),
            }

    except Exception as error:

        print(
            "PARTH METADATA FAILED:",
            repr(error),
        )

    # -----------------------------------------------------
    # YT-DLP METADATA FALLBACK
    # -----------------------------------------------------

    command = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--no-playlist",
        clean_url,
    ]

    try:

        result = _run_ytdlp(
            command,
            timeout=60,
        )

        if result.returncode != 0:

            print(
                "YTDLP METADATA ERROR:",
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
            "YTDLP METADATA EXCEPTION:",
            repr(error),
        )

        return {
            "title": "",
            "description": "",
            "uploader": "",
        }


# =========================================================
# DOWNLOAD URL DIRECTLY
# =========================================================

def _download_url(
    url,
    output_path,
):
    """
    Download an extracted Instagram CDN URL
    directly into /tmp.
    """

    response = requests.get(
        url,
        stream=True,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "(Linux; Android 10; K) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0 Mobile Safari/537.36",
        },
    )

    response.raise_for_status()

    with open(
        output_path,
        "wb",
    ) as file:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:

                file.write(
                    chunk
                )

    return output_path


# =========================================================
# PARTH-DL DOWNLOADER
# =========================================================

def _download_parth(
    url,
    temp_dir,
):
    """
    Download Instagram media using parth-dl.

    IMPORTANT:
    Vercel filesystem is read-only except /tmp.

    Therefore every output path is explicitly placed
    inside temp_dir.
    """

    import parth_dl

    clean_url = clean_instagram_url(
        url
    )

    print(
        "PARTH-DL:",
        clean_url,
    )

    # -----------------------------------------------------
    # FIRST: try normal file download
    # -----------------------------------------------------

    output_base = os.path.join(
        temp_dir,
        "instagram_media",
    )

    try:

        signature = getattr(
            parth_dl.download,
            "__signature__",
            None,
        )

        print(
            "PARTH DOWNLOAD SIGNATURE:",
            signature,
        )

    except Exception:
        pass

    # -----------------------------------------------------
    # Get information first.
    # This is important for carousel posts.
    # -----------------------------------------------------

    info = parth_dl.info(
        clean_url
    )

    if not isinstance(
        info,
        dict,
    ):

        raise RuntimeError(
            "Parth-dl returned invalid information."
        )

    print(
        "PARTH INFO TYPE:",
        info.get("type"),
    )

    # -----------------------------------------------------
    # CAROUSEL / IMAGE POST
    # -----------------------------------------------------

    images = info.get(
        "images"
    )

    entries = info.get(
        "entries"
    )

    if not images and isinstance(
        entries,
        list,
    ):

        images = []

        for entry in entries:

            if not isinstance(
                entry,
                dict,
            ):
                continue

            if entry.get(
                "kind"
            ) != "image":

                continue

            formats = entry.get(
                "formats"
            ) or []

            if not formats:
                continue

            image_url = formats[0].get(
                "url"
            )

            if image_url:

                images.append(
                    image_url
                )

    if images:

        files = []

        for index, image in enumerate(
            images,
            start=1,
        ):

            # -------------------------------------------------
            # Handle both:
            #   {"url": "..."}
            # and:
            #   "https://..."
            # -------------------------------------------------

            if isinstance(
                image,
                dict,
            ):

                image_url = (
                    image.get("url")
                    or image.get("src")
                    or ""
                )

            else:

                image_url = str(
                    image
                )

            if not image_url:
                continue

            output_path = os.path.join(
                temp_dir,
                f"image_{index:03d}.jpg",
            )

            print(
                "DOWNLOADING IMAGE:",
                index,
                image_url[:120],
            )

            try:

                _download_url(
                    image_url,
                    output_path,
                )

                if os.path.isfile(
                    output_path
                ):

                    files.append(
                        output_path
                    )

            except Exception as error:

                print(
                    "IMAGE DOWNLOAD FAILED:",
                    index,
                    repr(error),
                )

        if files:

            return files

        raise RuntimeError(
            "Parth-dl found images but none "
            "could be downloaded."
        )

    # -----------------------------------------------------
    # REEL / VIDEO
    # -----------------------------------------------------

    try:

        result = parth_dl.download(
            clean_url,
            output_path=output_base,
            quality="best",
            verbose=False,
        )

    except TypeError:

        # Some versions may not accept
        # output_path in the same way.
        #
        # In that case use the current temporary
        # directory as working directory.

        current_dir = os.getcwd()

        try:

            os.chdir(
                temp_dir
            )

            result = parth_dl.download(
                clean_url,
                quality="best",
                verbose=False,
            )

        finally:

            os.chdir(
                current_dir
            )

    print(
        "PARTH DOWNLOAD RESULT:",
        repr(result),
    )

    # -----------------------------------------------------
    # Collect files created inside /tmp.
    # -----------------------------------------------------

    files = []

    for root, _, filenames in os.walk(
        temp_dir
    ):

        for filename in filenames:

            path = os.path.join(
                root,
                filename,
            )

            if not os.path.isfile(
                path
            ):
                continue

            # Ignore partial/metadata files.
            if filename.endswith(
                (
                    ".part",
                    ".part.json",
                    ".json",
                )
            ):
                continue

            files.append(
                path
            )

    if files:

        return sorted(
            files
        )

    raise RuntimeError(
        "Parth-dl did not create a media file."
    )


# =========================================================
# YT-DLP DOWNLOADER
# =========================================================

def _download_ytdlp(
    url,
    temp_dir,
):

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

        clean_instagram_url(
            url
        ),
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
            filename,
        )

        if not os.path.isfile(
            path
        ):
            continue

        if filename.endswith(
            (
                ".part",
                ".part.json",
            )
        ):
            continue

        files.append(
            path
        )

    if not files:

        raise RuntimeError(
            "yt-dlp created no media file."
        )

    return files


# =========================================================
# MAIN DOWNLOAD FUNCTION
# =========================================================

def download_instagram_media(
    url
):
    """
    Main downloader.

    Priority:

        1. Parth-dl
        2. yt-dlp fallback

    Everything is stored in /tmp.
    """

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_",
        dir="/tmp",
    )

    print(
        "STARTING INSTAGRAM DOWNLOAD:",
        url,
    )

    # -----------------------------------------------------
    # PARTH-DL
    # -----------------------------------------------------

    try:

        files = _download_parth(
            url,
            temp_dir,
        )

        if files:

            print(
                "PARTH-DL SUCCESS:",
                files,
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

        # Remove anything Parth left behind
        # before trying yt-dlp.
        for filename in os.listdir(
            temp_dir
        ):

            path = os.path.join(
                temp_dir,
                filename,
            )

            try:

                if os.path.isdir(
                    path
                ):

                    shutil.rmtree(
                        path,
                        ignore_errors=True,
                    )

                else:

                    os.remove(
                        path
                    )

            except Exception:
                pass

    # -----------------------------------------------------
    # YT-DLP FALLBACK
    # -----------------------------------------------------

    try:

        files = _download_ytdlp(
            url,
            temp_dir,
        )

        print(
            "YTDLP SUCCESS:",
            files,
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
            "Both parth-dl and yt-dlp failed."
        )


# =========================================================
# CLEANUP
# =========================================================

def cleanup_media(
    temp_dir
):

    if not temp_dir:
        return

    try:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        print(
            "TEMP CLEANUP:",
            temp_dir,
        )

    except Exception as error:

        print(
            "TEMP CLEANUP ERROR:",
            repr(error),
)
