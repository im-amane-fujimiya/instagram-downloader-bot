import json
import os
import shutil
import subprocess
import sys
import tempfile
import inspect

from config import DOWNLOAD_TIMEOUT


YTDLP_FORMAT = (
    "best[height<=720][filesize<45M]/"
    "best[height<=720]/"
    "best[filesize<45M]/"
    "best"
)


def _empty_metadata():
    return {
        "title": "",
        "description": "",
        "uploader": "",
    }


def _clean_url(url):
    url = (url or "").strip()

    if "?" in url:
        url = url.split("?", 1)[0]

    return url.rstrip("/")


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


def _run_ytdlp(args, timeout=DOWNLOAD_TIMEOUT):

    command = [
        sys.executable,
        "-m",
        "yt_dlp",
    ]

    command.extend(args)

    print(
        "YTDLP:",
        " ".join(command),
    )

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


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
# PARTH METADATA
# =========================================================

def _parth_metadata(url):

    parth = _get_parth()

    if not parth:
        return _empty_metadata()

    try:

        info = parth.get_info(
            _clean_url(url)
        )

        print(
            "PARTH INFO:",
            repr(info),
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
# YTDLP METADATA
# =========================================================

def _ytdlp_metadata(url):

    args = [
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--no-playlist",
        _clean_url(url),
    ]

    try:

        result = _run_ytdlp(
            args,
            timeout=60,
        )

        if result.returncode != 0:

            print(
                "YTDLP METADATA ERROR:",
                result.stderr[-2000:],
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
# PARTH DOWNLOAD
# =========================================================

def _download_with_parth(
    url,
    temp_dir,
):

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

    # -----------------------------------------------------
    # IMPORTANT:
    # Do NOT use output_dir.
    # parth-dl 1.2.1 does not accept it.
    # -----------------------------------------------------

    signature = inspect.signature(
        parth.download
    )

    print(
        "PARTH DOWNLOAD SIGNATURE:",
        signature,
    )

    # Try the supported simple call.
    result = parth.download(
        clean_url
    )

    print(
        "PARTH RESULT:",
        repr(result),
    )

    # -----------------------------------------------------
    # parth-dl may return a path/list/object.
    # -----------------------------------------------------

    possible_files = []

    if isinstance(result, str):

        if os.path.isfile(result):
            possible_files.append(
                result
            )

        elif os.path.isdir(result):

            possible_files.extend(
                _collect_files(result)
            )

    elif isinstance(result, (list, tuple)):

        for item in result:

            if isinstance(item, str):
                if os.path.isfile(item):
                    possible_files.append(
                        item
                    )

    elif isinstance(result, dict):

        for key in (
            "path",
            "file",
            "filename",
            "filepath",
        ):

            value = result.get(key)

            if (
                isinstance(value, str)
                and os.path.isfile(value)
            ):
                possible_files.append(
                    value
                )

    # -----------------------------------------------------
    # Also inspect /tmp because parth-dl may create
    # its own temporary directory.
    # -----------------------------------------------------

    if not possible_files:

        for root, dirs, filenames in os.walk(
            "/tmp"
        ):

            for filename in filenames:

                path = os.path.join(
                    root,
                    filename,
                )

                if not os.path.isfile(path):
                    continue

                # Only media files.
                lower = filename.lower()

                if lower.endswith(
                    (
                        ".mp4",
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".heic",
                        ".mov",
                        ".m4v",
                    )
                ):

                    possible_files.append(
                        path
                    )

    if not possible_files:

        raise RuntimeError(
            "parth-dl completed but "
            "no media file was found."
        )

    # -----------------------------------------------------
    # Move/copy files into our own temp directory.
    # -----------------------------------------------------

    final_files = []

    for index, source in enumerate(
        possible_files
    ):

        if not os.path.isfile(source):
            continue

        extension = os.path.splitext(
            source
        )[1]

        destination = os.path.join(
            temp_dir,
            f"{index + 1}{extension}",
        )

        try:

            shutil.copy2(
                source,
                destination,
            )

            final_files.append(
                destination
            )

        except Exception as error:

            print(
                "PARTH COPY ERROR:",
                repr(error),
            )

    if not final_files:

        raise RuntimeError(
            "parth-dl media could not "
            "be copied."
        )

    print(
        "PARTH FILES:",
        final_files,
    )

    return final_files


# =========================================================
# YTDLP DOWNLOAD
# =========================================================

def _download_with_ytdlp(
    url,
    temp_dir,
):

    output = os.path.join(
        temp_dir,
        "%(playlist_index)s_%(id)s.%(ext)s",
    )

    args = [
        "--no-warnings",
        "--restrict-filenames",
        "--yes-playlist",

        "-f",
        YTDLP_FORMAT,

        "-o",
        output,

        _clean_url(url),
    ]

    result = _run_ytdlp(
        args
    )

    print(
        "YTDLP RETURN CODE:",
        result.returncode,
    )

    if result.stderr:

        print(
            "YTDLP STDERR:",
            result.stderr[-5000:],
        )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr[-2500:]
            or "yt-dlp failed."
        )

    files = _collect_files(
        temp_dir
    )

    if not files:

        raise RuntimeError(
            "yt-dlp finished but "
            "no media file was created."
        )

    print(
        "YTDLP FILES:",
        files,
    )

    return files


# =========================================================
# MAIN DOWNLOAD
# =========================================================

def download_instagram_media(url):

    """
    Primary:

        parth-dl

    Fallback:

        yt-dlp through Python module

    Returns:

        temp_dir,
        files
    """

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_"
    )

    # -----------------------------------------------------
    # PARTH
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

    # -----------------------------------------------------
    # Reset temp directory
    # -----------------------------------------------------

    shutil.rmtree(
        temp_dir,
        ignore_errors=True,
    )

    temp_dir = tempfile.mkdtemp(
        prefix="instagram_"
    )

    # -----------------------------------------------------
    # YT-DLP
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
            "Both parth-dl and yt-dlp failed."
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
