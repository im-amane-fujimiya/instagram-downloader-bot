import json
import subprocess


def get_instagram_metadata(url):
    """
    Metadata failure must NEVER stop the download.
    """

    try:
        command = [
            "yt-dlp",
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--no-playlist",
            url,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
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
            }

        data = json.loads(
            result.stdout
        )

        title = (
            data.get("title")
            or ""
        ).strip()

        description = (
            data.get("description")
            or ""
        ).strip()

        return {
            "title": title,
            "description": description,
        }

    except Exception as error:

        print(
            "METADATA EXCEPTION:",
            repr(error),
        )

        return {
            "title": "",
            "description": "",
        }
