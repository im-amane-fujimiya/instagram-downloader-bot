import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit

import requests

from config import DOWNLOAD_TIMEOUT


# ============================================================
# SETTINGS
# ============================================================

MAX_FILE_SIZE = 49 * 1024 * 1024

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


# ============================================================
# URL CLEANER
# ============================================================

def clean_instagram_url(url):
    """
    Remove Instagram tracking query parameters.

    Example:
        https://www.instagram.com/reel/ABC/?igsh=xxxx

    becomes:
        https://www.instagram.com/reel/ABC/
    """

    try:
        parts = urlsplit(url.strip())

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                "",
                "",
            )
        )

    except Exception:
        return url.strip()


# ============================================================
# INSTAGRAM TYPE
# ============================================================

def get_instagram_type(url):
    """
    Returns:
        reel
        post
        tv
        unknown
    """

    url = clean_instagram_url(url).lower()

    if "/reel/" in url:
        return "reel"

    if "/p/" in url:
        return "post"

    if "/tv/" in url:
        return "tv"

    return "unknown"


# ============================================================
# YT-DLP RUNNER
# ============================================================

def _run_ytdlp(
    command,
    timeout=DOWNLOAD_TIMEOUT,
):
    """
    Always run yt-dlp through Python.

    This fixes Render errors like:

        FileNotFoundError: No such file or directory

    caused by calling the `yt-dlp` executable directly.
    """

    full_command = [
        sys.executable,
        "-m",
        "yt_dlp",
    ] + command

    print(
        "YT-DLP COMMAND:",
        " ".join(full_command),
    )

    return subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ============================================================
# PARTH-DL IMPORT
# ============================================================

def _load_parth():
    """
    Import parth-dl safely.
    """

    try:
        import parth_dl

        return parth_dl

    except Exception as error:

        print(
            "PARTH IMPORT FAILED:",
            repr(error),
        )

        return None


# ============================================================
# PARTH METADATA
# ============================================================

def _get_parth_info(url):
    """
    parth-dl 1.2.1 uses:

        get_info(url)

    NOT:

        info(url)
    """

    parth = _load_parth()

    if parth is None:
        return None

    get_info = getattr(
        parth,
        "get_info",
        None,
    )

    if not callable(get_info):

        print(
            "PARTH ERROR: get_info() not available"
        )

        return None

    try:

        clean_url = clean_instagram_url(url)

        print(
            "PARTH INFO:",
            clean_url,
        )

        data = get_info(
            clean_url
        )

        print(
            "PARTH INFO RESULT:",
            data,
        )

        if isinstance(data, dict):
            return data

        return None

    except Exception as error:

        print(
            "PARTH METADATA FAILED:",
            repr(error),
        )

        return None


# ============================================================
# GENERIC METADATA
# ============================================================

def get_instagram_metadata(url):

    """
    Metadata priority:

        1. parth-dl
        2. yt-dlp

    Metadata failure NEVER stops download.
    """

    # --------------------------------------------------------
    # PARTH
    # --------------------------------------------------------

    try:

        data = _get_parth_info(url)

        if data:

            title = str(
                data.get("title")
                or data.get("caption")
                or ""
            ).strip()

            description = str(
                data.get("description")
                or data.get("caption")
                or ""
            ).strip()

            uploader = str(
                data.get("uploader")
                or data.get("username")
                or data.get("owner")
                or ""
            ).strip()

            print(
                "METADATA SOURCE: parth-dl"
            )

            return {
                "title": title,
                "description": description,
                "uploader": uploader,
            }

    except Exception as error:

        print(
            "PARTH METADATA ERROR:",
            repr(error),
        )

    # --------------------------------------------------------
    # YT-DLP
    # --------------------------------------------------------

    command = [
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--no-playlist",
        clean_instagram_url(url),
    ]

    try:

        result = _run_ytdlp(
            command,
            timeout=60,
        )

        if result.returncode != 0:

            print(
                "YTDLP METADATA ERROR:",
                result.stderr[-1500:],
            )

            return {
                "title": "",
                "description": "",
                "uploader": "",
            }

        data = json.loads(
            result.stdout
        )

        print(
            "METADATA SOURCE: yt-dlp"
        )

        return {
            "title": str(
                data.get("title")
                or ""
            ).strip(),

            "description": str(
                data.get("description")
                or ""
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


# ============================================================
# FILE EXTENSION
# ============================================================

def _extension_from_content_type(
    content_type,
):

    content_type = (
        content_type or ""
    ).lower()

    if "jpeg" in content_type:
        return ".jpg"

    if "png" in content_type:
        return ".png"

    if "webp" in content_type:
        return ".webp"

    if "mp4" in content_type:
        return ".mp4"

    if "quicktime" in content_type:
        return ".mov"

    if "webm" in content_type:
        return ".webm"

    return ".bin"


def _extension_from_url(
    url,
    content_type="",
):

    """
    Instagram sometimes gives a .heic URL while
    actually serving JPEG because of:

        stp=dst-jpg_...

    Prefer content type.
    """

    content_type = (
        content_type or ""
    ).lower()

    if "image/" in content_type:

        return _extension_from_content_type(
            content_type
        )

    lower_url = url.lower()

    if "dst-jpg" in lower_url:
        return ".jpg"

    path = urlsplit(
        url
    ).path.lower()

    match = re.search(
        r"\.(jpg|jpeg|png|webp|mp4|mov|webm)(?:$|\?)",
        path,
    )

    if match:
        ext = match.group(1)

        if ext == "jpeg":
            ext = "jpg"

        return "." + ext

    return ".bin"


# ============================================================
# DOWNLOAD DIRECT URL
# ============================================================

def _download_url(
    url,
    output_path,
):

    print(
        "DOWNLOADING CDN:",
        url[:180],
    )

    response = requests.get(
        url,
        headers=HEADERS,
        stream=True,
        timeout=DOWNLOAD_TIMEOUT,
    )

    response.raise_for_status()

    content_length = response.headers.get(
        "Content-Length"
    )

    if content_length:

        try:

            if int(content_length) > MAX_FILE_SIZE:

                raise RuntimeError(
                    "Media file is larger than Telegram limit."
                )

        except ValueError:
            pass

    with open(
        output_path,
        "wb",
    ) as file:

        total = 0

        for chunk in response.iter_content(
            chunk_size=1024 * 256
        ):

            if not chunk:
                continue

            total += len(chunk)

            if total > MAX_FILE_SIZE:

                raise RuntimeError(
                    "Media file is larger than Telegram limit."
                )

            file.write(chunk)

    if not os.path.exists(
        output_path
    ):

        raise RuntimeError(
            "Downloaded file does not exist."
        )

    if os.path.getsize(
        output_path
    ) == 0:

        raise RuntimeError(
            "Downloaded file is empty."
        )

    print(
        "DOWNLOADED:",
        output_path,
        os.path.getsize(output_path),
        "bytes",
    )

    return output_path


# ============================================================
# PARTH POST / CAROUSEL DOWNLOADER
# ============================================================

def _download_with_parth(
    url,
    temp_dir,
):

    data = _get_parth_info(
        url
    )

    if not data:

        raise RuntimeError(
            "parth-dl could not extract Instagram post."
        )

    entries = data.get(
        "entries"
    )

    # --------------------------------------------------------
    # Some versions expose images directly.
    # --------------------------------------------------------

    if not entries:

        images = data.get(
            "images"
        )

        if images:

            entries = [
                {
                    "kind": "image",
                    "formats": [
                        {
                            "url": image.get("url")
                            if isinstance(image, dict)
                            else image
                        }
                    ],
                }
                for image in images
            ]

    if not entries:

        raise RuntimeError(
            "parth-dl returned no media entries."
        )

    files = []

    index = 0

    for entry in entries:

        if not isinstance(
            entry,
            dict,
        ):
            continue

        kind = str(
            entry.get("kind")
            or "image"
        ).lower()

        formats = entry.get(
            "formats"
        ) or []

        media_url = None

        # ----------------------------------------------------
        # Find first usable format.
        # ----------------------------------------------------

        for fmt in formats:

            if not isinstance(
                fmt,
                dict,
            ):
                continue

            candidate = fmt.get(
                "url"
            )

            if candidate:

                media_url = candidate
                break

        if not media_url:

            direct_url = entry.get(
                "url"
            )

            if direct_url:
                media_url = direct_url

        if not media_url:
            continue

        index += 1

        # ----------------------------------------------------
        # First save with temporary extension.
        # ----------------------------------------------------

        temp_path = os.path.join(
            temp_dir,
            f"parth_{index}.download",
        )

        try:

            _download_url(
                media_url,
                temp_path,
            )

            # -----------------------------------------------
            # Detect actual content.
            # -----------------------------------------------

            try:

                probe = requests.head(
                    media_url,
                    headers=HEADERS,
                    timeout=20,
                    allow_redirects=True,
                )

                content_type = (
                    probe.headers.get(
                        "Content-Type",
                        "",
                    )
                )

            except Exception:

                content_type = ""

            ext = _extension_from_url(
                media_url,
                content_type,
            )

            # If kind is video, prefer mp4.
            if kind == "video":

                if "mp4" in media_url.lower():
                    ext = ".mp4"

                elif not ext in (
                    ".mp4",
                    ".mov",
                    ".webm",
                ):
                    ext = ".mp4"

            final_path = os.path.join(
                temp_dir,
                f"{index:02d}{ext}",
            )

            os.replace(
                temp_path,
                final_path,
            )

            files.append(
                final_path
            )

        except Exception as error:

            print(
                "PARTH MEDIA FAILED:",
                index,
                repr(error),
            )

            try:
                if os.path.exists(
                    temp_path
                ):
                    os.remove(
                        temp_path
                    )
            except Exception:
                pass

    if not files:

        raise RuntimeError(
            "parth-dl found media but none could be downloaded."
        )

    print(
        "PARTH FILES:",
        files,
    )

    return (
        temp_dir,
        files,
    )


# ============================================================
# YT-DLP REEL DOWNLOADER
# ============================================================

def _download_with_ytdlp(
    url,
    temp_dir,
):

    output = os.path.join(
        temp_dir,
        "%(playlist_index)s_%(id)s.%(ext)s",
    )

    command = [
        "--no-warnings",
        "--restrict-filenames",
        "--no-playlist",

        # Telegram-friendly quality.
        "-f",
        (
            "best[height<=720][filesize<45M]/"
            "best[height<=720]/"
            "best[filesize<45M]/"
            "best"
        ),

        "-o",
        output,

        clean_instagram_url(url),
    ]

    result = _run_ytdlp(
        command
    )

    print(
        "YTDLP RETURN CODE:",
        result.returncode,
    )

    if result.stdout:

        print(
            "YTDLP STDOUT:",
            result.stdout[-2000:],
        )

    if result.stderr:

        print(
            "YTDLP STDERR:",
            result.stderr[-3000:],
        )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr[-2000:]
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
                ".ytdl",
            )
        ):
            continue

        files.append(
            path
        )

    if not files:

        raise RuntimeError(
            "yt-dlp completed but no media file was created."
        )

    print(
        "YTDLP FILES:",
        files,
    )

    return (
        temp_dir,
        files,
    )


# ============================================================
# MAIN DOWNLOAD FUNCTION
# ============================================================

def download_instagram_media(url):

    """
    Final downloader architecture:

        /reel/ -> yt-dlp
        /p/    -> parth-dl
        /tv/   -> parth-dl first, yt-dlp fallback

    Returns:

        temp_dir,
        files
    """

    clean_url = clean_instagram_url(
        url
    )

    media_type = get_instagram_type(
        clean_url
    )

    print(
        "STARTING INSTAGRAM DOWNLOAD:",
        clean_url,
    )

    print(
        "INSTAGRAM TYPE:",
        media_type,
    )

    # ========================================================
    # REEL
    # ========================================================

    if media_type == "reel":

        temp_dir = tempfile.mkdtemp(
            prefix="instagram_reel_"
        )

        try:

            return _download_with_ytdlp(
                clean_url,
                temp_dir,
            )

        except Exception as error:

            print(
                "YTDLP REEL FAILED:",
                repr(error),
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )

            # Parth fallback
            temp_dir = tempfile.mkdtemp(
                prefix="instagram_reel_parth_"
            )

            try:

                return _download_with_parth(
                    clean_url,
                    temp_dir,
                )

            except Exception:

                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True,
                )

                raise RuntimeError(
                    "Both yt-dlp and parth-dl failed for this reel."
                )

    # ========================================================
    # POST / CAROUSEL
    # ========================================================

    if media_type == "post":

        temp_dir = tempfile.mkdtemp(
            prefix="instagram_post_"
        )

        try:

            return _download_with_parth(
                clean_url,
                temp_dir,
            )

        except Exception as error:

            print(
                "PARTH POST FAILED:",
                repr(error),
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )

            # yt-dlp fallback
            temp_dir = tempfile.mkdtemp(
                prefix="instagram_post_ytdlp_"
            )

            try:

                return _download_with_ytdlp(
                    clean_url,
                    temp_dir,
                )

            except Exception:

                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True,
                )

                raise RuntimeError(
                    "Both parth-dl and yt-dlp failed for this post."
                )

    # ========================================================
    # TV / UNKNOWN
    # ========================================================

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_media_"
    )

    try:

        return _download_with_parth(
            clean_url,
            temp_dir,
        )

    except Exception as parth_error:

        print(
            "PARTH FALLBACK FAILED:",
            repr(parth_error),
        )

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_ytdlp_"
    )

    try:

        return _download_with_ytdlp(
            clean_url,
            temp_dir,
        )

    except Exception:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        raise RuntimeError(
            "Both Instagram download methods failed."
        )


# ============================================================
# CLEANUP
# ============================================================

def cleanup_media(
    temp_dir
):

    if temp_dir:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
    )
