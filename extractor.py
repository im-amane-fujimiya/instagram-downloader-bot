import tempfile
import shutil
from pathlib import Path

from parth_dl import (
    download,
    DownloadError,
    RateLimitError,
    NetworkError,
    ValidationError,
)


def extract_instagram_media(url):
    """
    Download public Instagram media.

    Supports:
    - Reels
    - Video posts
    - Single photos
    - Carousels
    """

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="instagram_"
        )
    )

    try:
        result = download(
            url,
            output_path=str(temp_dir),
            quality="best",
        )

        # Single media returns a string.
        if isinstance(result, str):
            files = [result]

        # Carousel returns a list.
        elif isinstance(result, list):
            files = result

        else:
            files = []

        # Fallback: look inside temp directory.
        if not files:
            files = [
                str(path)
                for path in temp_dir.rglob("*")
                if path.is_file()
            ]

        if not files:
            raise DownloadError(
                "No media files were downloaded."
            )

        return str(temp_dir), files

    except RateLimitError:
        cleanup_media(temp_dir)
        raise RuntimeError(
            "Instagram is temporarily rate-limiting requests. "
            "Please try again later."
        )

    except ValidationError:
        cleanup_media(temp_dir)
        raise RuntimeError(
            "Invalid or unsupported Instagram URL."
        )

    except NetworkError as error:
        cleanup_media(temp_dir)
        raise RuntimeError(
            f"Instagram network error: {error}"
        )

    except DownloadError as error:
        cleanup_media(temp_dir)
        raise RuntimeError(
            f"Instagram download failed: {error}"
        )

    except Exception:
        cleanup_media(temp_dir)
        raise


def cleanup_media(temp_dir):
    """
    Delete temporary downloaded files.
    """
    if temp_dir:
        shutil.rmtree(
            str(temp_dir),
            ignore_errors=True
        )
        
