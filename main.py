from flask import Flask, request
import os, requests, re

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@Material_01_01"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ========== ALAG ALAG FUNCTIONS ==========

def func_get_caption(html):
    try:
        m = re.search(r'"caption":\{"text":"([^"]+)"', html)
        if m: return m.group(1).encode().decode('unicode_escape')[:800]
        m2 = re.search(r'"edge_media_to_caption":\{"edges":\[{"node":\{"text":"([^"]+)"', html)
        if m2: return m2.group(1).encode().decode('unicode_escape')[:800]
    except: pass
    return ""

def func_get_username(html):
    try:
        m = re.search(r'"owner":\{"username":"([^"]+)"', html)
        if m: return m.group(1)
    except: pass
    return "Instagram"

def func_get_photos(html):
    try:
        raw = re.findall(r'"display_url":"([^"]+)"', html)
        clean = []
        for u in raw:
            cu = u.replace('\\u0026','&').encode().decode('unicode_escape')
            if 's150x150' not in cu and cu not in clean:
                clean.append(cu)
        return clean[:10]
    except: return []

def func_get_video_link(url):
    # Sirf video ke liye yt-dlp - photo/caption ke liye nahi
    try:
        import yt_dlp
        opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            vurl = info.get('url') or (info.get('formats')[-1]['url'] if info.get('formats') else None)
            return vurl, info.get('description','')[:500], info.get('uploader','Insta')
    except: return None, "", ""

def func_get_profile_dp(username):
    try:
        html = requests.get(f"https://www.instagram.com/{username}/", headers=HEADERS, timeout=10).text
        m = re.search(r'"profile_pic_url_hd":"([^"]+)"', html)
        if m: return m.group(1).replace('\\u0026','&')
    except: pass
    return None

def sb_add_user(chat_id, username=""):
    if not SUPABASE_URL or not SUPABASE_KEY: return
    try:
        h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
        requests.post(f"{SUPABASE_URL}/rest/v1/users", headers={**h, "Prefer": "resolution=merge-duplicates"}, json={"chat_id": chat_id, "username": username}, timeout=4)
    except: pass

# ========== BOT ==========

@app.route("/", methods=["GET"])
def home(): return "MONSTER V3 - SEPARATE FUNCTIONS 🔥"

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        username = data["message"]["from"].get("username","")
        sb_add_user(chat_id, username)

        # Commands
        if text.startswith("/start"):
            kb = {"inline_keyboard": [[{"text": "📥 Download", "callback_data": "dl"}], [{"text": f"📢 {CHANNEL_ID}", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}]]}
            try:
                requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": START_PHOTO, "caption": "🎬 <b>Instagram Downloader Bot</b>\n\n🎞 Reels 🎥 Videos 🖼 Photos\n\n⚡️ Har cheez alag function se!\n\n🔥 Link bhej!", "parse_mode": "HTML", "reply_markup": kb}, timeout=10)
            except:
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": "🎬 Bot ON! Link bhej!", "reply_markup": kb}, timeout=10)
            return "ok",200

        if text.startswith("/id"):
            requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": f"🆔 <code>{chat_id}</code>", "parse_mode": "HTML"}, timeout=5)
            return "ok",200

        if text.startswith("/profile"):
            uname = text.replace("/profile","").strip().replace("@","")
            if not uname:
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": "Use: /profile username"}, timeout=5)
                return "ok",200
            dp = func_get_profile_dp(uname)
            if dp: requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": dp, "caption": f"👤 @{uname} HD DP"}, timeout=10)
            else: requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": "❌ DP nahi mila"}, timeout=5)
            return "ok",200

        # Main downloader - ALAG ALAG
        links = re.findall(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not links: return "ok",200

        for url in links[:2]:
            try:
                # Step 1: HTML lao (photo + caption ke liye) - yt-dlp nahi
                html = requests.get(url, headers=HEADERS, timeout=10).text
                caption = func_get_caption(html)
                uname = func_get_username(html)
                photos = func_get_photos(html)

                # Photo hai to photo bhejo
                if photos and "reel" not in url and "/p/" in url:
                    for i, p in enumerate(photos[:5]):
                        cap = f"👤 @{uname}\n\n{caption}" if i==0 else ""
                        requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": p, "caption": cap[:1024]}, timeout=15)
                    continue

                # Video/Reel hai to alag function
                vurl, vdesc, vuploader = func_get_video_link(url)
                if vurl:
                    final_cap = caption or vdesc
                    cap = f"👤 @{vuploader or uname}\n\n{final_cap}"[:1024]
                    requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": vurl, "caption": cap}, timeout=20)
                    # Channel auto-post
                    try: requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": CHANNEL_ID, "video": vurl, "caption": cap[:300]}, timeout=10)
                    except: pass
                else:
                    # Fallback photo
                    if photos:
                        requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": photos[0], "caption": f"👤 @{uname}\n\n{caption}"[:1024]}, timeout=10)
            except Exception as e:
                print("DL ERR", e)

    except Exception as e:
        print("MAIN ERR", e)
    return "ok",200
