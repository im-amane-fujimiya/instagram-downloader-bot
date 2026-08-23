import requests
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_url(u):
    try:
        return u.replace('\u0026', '&').encode().decode('unicode_escape')
    except:
        return u

def extract_meta(html):
    username = "Instagram"
    caption = ""
    try:
        m1 = re.search(r'"owner":\{"username":"([^"]+)"', html)
        if m1: username = m1.group(1)
    except: pass
    try:
        m2 = re.search(r'"caption":\{"text":"([^"]+)"', html)
        if m2: caption = m2.group(1)[:500]
    except: pass
    return username, caption

def download_insta(url):
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'skip_download': True, 'http_headers': HEADERS}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and (info.get('url') or info.get('formats')):
                info['type'] = 'video'
                info['uploader'] = info.get('uploader') or "Instagram"
                info['caption'] = info.get('description') or ""
                return info
    except Exception as e:
        print(f"yt-dlp skip: {e}")

    try:
        html = requests.get(url, headers=HEADERS, timeout=15).text
        username, caption = extract_meta(html)
        m = re.search(r'"video_url":"([^"]+)"', html)
        if m:
            return {'type': 'video', 'url': clean_url(m.group(1)), 'uploader': username, 'caption': caption, 'formats': [{'url': clean_url(m.group(1))}]}

        raw = re.findall(r'"display_url":"([^"]+)"', html)
        imgs = []
        for u in raw:
            cu = clean_url(u)
            if cu not in imgs and 's150x150' not in cu:
                imgs.append(cu)
        if imgs:
            return {'type': 'carousel' if len(imgs)>1 else 'photo', 'images': imgs[:10], 'uploader': username, 'caption': caption}
    except Exception as e:
        print(f"scrape fail: {e}")

    raise Exception("No media found")
