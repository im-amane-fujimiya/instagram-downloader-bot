import yt_dlp
import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def extract_info(url):
    # Method 1: yt-dlp try karo
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'http_headers': HEADERS,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and (info.get('url') or info.get('formats')):
                return info
    except Exception as e:
        print(f"[yt-dlp fail] {e}")

    # Method 2: Direct scraping fallback (ye ab kaam karega)
    print("[Fallback] Trying direct scrape...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text

        # video_url nikalna
        match = re.search(r'"video_url":"([^"]+)"', html)
        if match:
            video_url = match.group(1).replace('\\u0026', '&').encode().decode('unicode_escape')

            # title / user nikalna
            user_match = re.search(r'"owner":\{"username":"([^"]+)"', html)
            caption_match = re.search(r'"caption":\{"text":"([^"]+)"', html)

            return {
                'url': video_url,
                'title': caption_match.group(1)[:100] if caption_match else "Instagram Reel",
                'uploader': user_match.group(1) if user_match else "Instagram",
                'ext': 'mp4',
                'formats': [{'url': video_url, 'ext': 'mp4'}]
            }
    except Exception as e:
        print(f"[Fallback fail] {e}")

    raise Exception("No video formats found")
