import subprocess
import json


def get_instagram_metadata(url):
    """
    Try to get Instagram title/caption using yt-dlp.
    Metadata failure must never stop the download.
    """

    try:
        command = [
            "yt-dlp",
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--no-playlist",
            url
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(
                "METADATA ERROR:",
                result.stderr[-1000:]
            )
            return {
                "title": "",
                "description": ""
            }

        data = json.loads(result.stdout)

        title = (
            data.get("title")
            or data.get("description")
            or ""
        )

        description = (
            data.get("description")
            or ""
        )

        return {
            "title": title.strip(),
            "description": description.strip()
        }

    except Exception as error:
        print(
            "METADATA EXCEPTION:",
            repr(error)
        )

        return {
            "title": "",
            "description": ""
          }
