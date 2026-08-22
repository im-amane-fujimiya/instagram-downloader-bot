import os
import shutil
import tempfile
import subprocess

from downloader import download_with_ytdlp
from extractor import extract_instagram_media, cleanup_media
from metadata import get_instagram_metadata


YTDLP_FORMAT = (
    "best[height<=720][filesize<80M]/"
    "best[height<=720]/"
    "best[filesize<80M]/"
    "best"
)


def get_metadata(url):
    """
    Get title + description.
    Metadata failure never stops downloading.
    """

    try:
        print("METADATA: fetching...")

        metadata = get_instagram_metadata(url)

        if not isinstance(metadata, dict):
            metadata = {}

        result = {
            "title": (
                metadata.get("title") or ""
            ).strip(),

            "description": (
                metadata.get("description") or ""
            ).strip()
        }

        print(
            "METADATA:",
            result
        )

        return result

    except Exception as error:

        print(
            "METADATA FAILED:",
            repr(error)
        )

        return {
            "title": "",
            "description": ""
        }


def build_caption(metadata):
    """
    Build Telegram media caption.
    """

    title = (
        metadata.get("title") or ""
    ).strip()

    description = (
        metadata.get("description") or ""
    ).strip()

    parts = []

    if title:
        parts.append(
            f"📝 {title}"
        )

    if description:
        parts.append(
            f"📄 {description}"
        )

    caption = "\n\n".join(parts)

    # Telegram media caption limit
    return caption[:1024]


def download_media(url):
    """
    Download Instagram media.

    1. Try yt-dlp
    2. If yt-dlp fails, use parth-dl extractor
    """

    ytdlp_dir = None
    extractor_dir = None

    try:

        print(
            "DOWNLOADER: trying yt-dlp..."
        )

        ytdlp_dir, files = (
            download_with_ytdlp(url)
        )

        print(
            "YTDLP SUCCESS:",
            files
        )

        return {
            "directory": ytdlp_dir,
            "files": files,
            "type": "ytdlp"
        }

    except Exception as error:

        print(
            "YTDLP FAILED:",
            repr(error)
        )

        if ytdlp_dir:
            shutil.rmtree(
                ytdlp_dir,
                ignore_errors=True
            )

    try:

        print(
            "EXTRACTOR: trying parth-dl..."
        )

        extractor_dir, files = (
            extract_instagram_media(url)
        )

        print(
            "EXTRACTOR SUCCESS:",
            files
        )

        return {
            "directory": extractor_dir,
            "files": files,
            "type": "extractor"
        }

    except Exception:

        if extractor_dir:
            cleanup_media(
                extractor_dir
            )

        raise


def process_instagram(url):
    """
    Main Instagram processing pipeline.

    Returns:
        {
            "files": [...],
            "directory": "...",
            "caption": "...",
            "metadata": {...},
            "downloader": "ytdlp/extractor"
        }
    """

    if not url:
        raise ValueError(
            "Instagram URL is empty."
        )

    # ---------------------------------------------
    # Metadata
    # ---------------------------------------------

    metadata = get_metadata(
        url
    )

    # ---------------------------------------------
    # Download
    # ---------------------------------------------

    download_result = download_media(
        url
    )

    files = download_result[
        "files"
    ]

    if not files:
        raise RuntimeError(
            "No media files were downloaded."
        )

    # ---------------------------------------------
    # Caption
    # ---------------------------------------------

    caption = build_caption(
        metadata
    )

    return {
        "files": files,

        "directory": (
            download_result[
                "directory"
            ]
        ),

        "caption": caption,

        "metadata": metadata,

        "downloader": (
            download_result[
                "type"
            ]
        )
    }


def cleanup_result(result):
    """
    Clean temporary downloaded files.
    """

    if not result:
        return

    directory = result.get(
        "directory"
    )

    if not directory:
        return

    try:

        if result.get(
            "downloader"
        ) == "extractor":

            cleanup_media(
                directory
            )

        else:

            shutil.rmtree(
                directory,
                ignore_errors=True
            )

    except Exception as error:

        print(
            "CORE CLEANUP ERROR:",
            repr(error)
      )
