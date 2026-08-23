import yt_dlp, requests, re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_url(u):
    return u.replace('\\u0026', '&').encode().decode('unicode_escape')

def clean_text(t):
    try: return t.encode().decode('unicode_escape')
    except: return t

def extract_meta(html):
    username = "Instagram"
    caption = ""
    try:
        um = re.search(r'"owner":\{"username":"([^"]+)"', html)
        if um: username = um.group(1)
    except: pass
    try:
        cm = re.search(r'"caption":\{"text":"([^"]+)"', html)
        if cm: caption = clean_text(cm.group(1))
    except: pass
    return username, caption

def download_insta_photo(url):
    html = requests.get(url, headers=HEADERS, timeout=15).text
    username, caption = extract_meta(html)
    raw_images = re.findall(r'"display_url":"([^"]+)"', html)
    images = []
    for u in raw_images:
        cu = clean_url(u)
        if cu not in images and 's150x150' not in cu:
            images.append(cu)
    return {'type': 'carousel' if len(images)>1 else 'photo', 'images': images[:10], 'uploader': username, 'title': caption, 'caption': caption}

def download_insta(url):
    ydl_opts = {'quiet': True, 'skip_download': True, 'http_headers': HEADERS}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and (info.get('url') or info.get('formats')):
                info['type'] = 'video'
                info['uploader'] = info.get('uploader') or "Instagram"
                info['caption'] = info.get('description') or info.get('title') or ""
                return info
    except: pass

    try:
        html = requests.get(url, headers=HEADERS, timeout=15).text
        username, caption = extract_meta(html)
        m = re.search(r'"video_url":"([^"]+)"', html)
        if m:
            return {'type': 'video', 'url': clean_url(m.group(1)), 'uploader': username, 'title': caption, 'caption': caption, 'formats': [{'url': clean_url(m.group(1))}]}
    except: pass
    return download_insta_photo(url)
