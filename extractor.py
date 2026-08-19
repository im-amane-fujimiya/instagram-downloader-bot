import os
import tempfile
from pathlib import Path

from parth_dl import download


def extract_instagram_media(url):
    """
    Download public Instagram media using parth-dl.

    Returns:
        list[str]: downloaded file paths
    """

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="instagram_"
        )
    )

    try:
        result = download(
            url,
            output_dir=str(temp_dir)
        )

        files = []

        for path in temp_dir.rglob("*"):
            if path.is_file():
                files.append(str(path))

        if not files:
            raise RuntimeError(
                "Instagram media was not found."
            )

        return temp_dir, files

    except Exception:
        # Keep the directory for the caller to clean up
        raise


def cleanup_media(temp_dir):
    """
    Delete temporary downloaded media.
    """

    if temp_dir and os.path.exists(temp_dir):
        import shutil

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )
