import re
from urllib.parse import urlparse


INSTAGRAM_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
}


def is_instagram_url(url):
    """Check whether a URL belongs to Instagram."""

    try:
        parsed = urlparse(url)

        host = parsed.netloc.lower().split(":")[0]

        return host in INSTAGRAM_HOSTS

    except Exception:
        return False


def clean_instagram_url(url):
    """Remove unnecessary query parameters/fragments."""

    parsed = urlparse(url)

    return (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
        f"{parsed.path}"
    )


def get_instagram_shortcode(url):
    """
    Extract the Instagram shortcode from common
    public Instagram URLs.
    """

    if not is_instagram_url(url):
        return None

    path = urlparse(url).path.strip("/")

    patterns = [
        r"^reel/([^/]+)",
        r"^reels/([^/]+)",
        r"^p/([^/]+)",
        r"^tv/([^/]+)",
    ]

    for pattern in patterns:
        match = re.match(
            pattern,
            path,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


def get_post_type(url):
    """
    Identify the basic Instagram URL type.

    This does NOT claim that the URL actually contains
    a photo/video; it only identifies the URL pattern.
    """

    if not is_instagram_url(url):
        return "unknown"

    path = urlparse(url).path.lower()

    if "/reel/" in path or "/reels/" in path:
        return "reel"

    if "/tv/" in path:
        return "video"

    if "/p/" in path:
        return "post"

    return "unknown"


def inspect_url(url):
    """
    Return information about an Instagram URL.
    """

    url = url.strip()

    return {
        "is_instagram": is_instagram_url(url),
        "clean_url": clean_instagram_url(url)
        if is_instagram_url(url)
        else None,
        "shortcode": get_instagram_shortcode(url),
        "type": get_post_type(url),
    }


def extract_media(url):
    """
    Placeholder for the actual Instagram media extractor.

    Returns metadata only for now.

    A real media extractor/backend should be plugged
    into this function once selected and tested.
    """

    info = inspect_url(url)

    if not info["is_instagram"]:
        raise ValueError(
            "Not a valid Instagram URL."
        )

    if not info["shortcode"]:
        raise ValueError(
            "Could not identify Instagram post."
        )

    return {
        "url": info["clean_url"],
        "shortcode": info["shortcode"],
        "type": info["type"],
        "media": [],
  }
