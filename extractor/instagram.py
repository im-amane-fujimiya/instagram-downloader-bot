import yt_dlp
import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def clean_url(u):
    return u.replace('\\u0026', '&').encode().decode('unicode_escape')

# 1. VIDEO KE LIYE - yt-dlp (tera wala idea)
def download_insta(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'http_headers': HEADERS,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('url') or info.get('formats'):
                info['type'] = 'video'
                return info
    except:
        pass

    # Fallback video scrape
    try:
        html = requests.get(url, headers=HEADERS, timeout=15).text
        m = re.search(r'"video_url":"([^"]+)"', html)
        if m:
            return {
                'type': 'video',
                'url': clean_url(m.group(1)),
                'title': 'Instagram Reel',
                'uploader': 'Instagram',
                'ext': 'mp4',
                'formats': [{'url': clean_url(m.group(1))}]
            }
    except:
        pass

    # Agar video nahi mila to photo try karo
    return download_insta_photo(url)

# 2. PHOTO KE LIYE - Naya function
def download_insta_photo(url):
    html = requests.get(url, headers=HEADERS, timeout=15).text

    # saare display_url nikal lo (carousel me 10 tak hote hai)
    raw_images = re.findall(r'"display_url":"([^"]+)"', html)
    # duplicate hatao
    images = []
    for u in raw_images:
        cu = clean_url(u)
        if cu not in images:
            images.append(cu)

    if not images:
        raise Exception("No photo/video found")

    if len(images) == 1:
        return {'type': 'photo', 'images': images}
    else:
        return {'type': 'carousel', 'images': images[:10]} # insta max 10

# alias
extract_info = download_insta
