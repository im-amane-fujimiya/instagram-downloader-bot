from flask import Flask, request
import os, requests, re, time, random

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") or os.getenv("ADMIN_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_TIME = time.time()
TOTAL = 0
USERS = set()

HEADERS = {"User-Agent": "Mozilla/5.0"}

START_PHOTO = "https://i.imgur.com/8Km9tLL.jpeg"
START_TEXT = """🎬 <b>Instagram Downloader Bot</b>

🎞 Reels
🎥 Videos
🖼 Photos
📚 Carousels

⚡️ Simple
🎯 Easy to use
🤖 Automated

Built to make saving public Instagram media a little less annoying 😎"""

CHAT_STYLE = [
    "👋 Link bhej de! Baki main sambhal lunga 😎",
    "😍 Bas link de, download mera kaam!",
    "🔥 Bhej de reel, turant laata hu!",
    "👑 Owner aa gaya! Link bhej de mere aaka!",
]

def clean_url(u):
    try: return u.replace('\u0026', '&').encode().decode('unicode_escape')
    except: return u

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
    except: pass
    html = requests.get(url, headers=HEADERS, timeout=15).text
    username, caption = "Instagram", ""
    try:
        m1 = re.search(r'"owner":\{"username":"([^"]+)"', html)
        if m1: username = m1.group(1)
        m2 = re.search(r'"caption":\{"text":"([^"]+)"', html)
        if m2: caption = m2.group(1)[:500]
    except: pass
    m = re.search(r'"video_url":"([^"]+)"', html)
    if m: return {'type': 'video', 'url': clean_url(m.group(1)), 'uploader': username, 'caption': caption, 'formats': [{'url': clean_url(m.group(1))}]}
    raw = re.findall(r'"display_url":"([^"]+)"', html)
    imgs = []
    for u in raw:
        cu = clean_url(u)
        if cu not in imgs and 's150x150' not in cu: imgs.append(cu)
    return {'type': 'carousel' if len(imgs)>1 else 'photo', 'images': imgs[:10], 'uploader': username, 'caption': caption}

def send_message(chat_id, text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10).json()
        if r.get("ok"): return r["result"]["message_id"]
    except: pass
    return None

def delete_message(chat_id, msg_id):
    try: requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
    except: pass

def send_video(chat_id, url, cap=""): requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": url, "caption": cap[:1024]}, timeout=20)
def send_photo(chat_id, url, cap=""): requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": url, "caption": cap[:1024]}, timeout=20)

@app.route("/", methods=["GET"])
def home(): return "Bot is running! 👑"

@app.route("/", methods=["POST"])
def webhook():
    global TOTAL
    loading_id = None
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        is_owner = OWNER_ID and str(chat_id).strip() == str(OWNER_ID).strip()
        USERS.add(chat_id)
        TOTAL+=1

        if text == "/id":
            send_message(chat_id, f"🆔 <b>Teri ID:</b> <code>{chat_id}</code>\n👑 Owner: {is_owner}")
            return "ok",200
        if text == "/ping":
            up = int(time.time()-START_TIME)
            send_message(chat_id, f"🏓 <b>Pong!</b>\n⏱ Uptime: {up//60}m {up%60}s\n📦 Total Requests: {TOTAL}")
            return "ok",200
        if text == "/stats":
            if not is_owner: send_message(chat_id, "❌ Ye sirf Owner ke liye hai!")
            else: send_message(chat_id, f"📊 <b>Stats</b>\n⏱ Uptime: {int(time.time()-START_TIME)//60}m\n👥 Users: {len(USERS)}\n📥 Total: {TOTAL}")
            return "ok",200
        if text.startswith("/broadcast"):
            if not is_owner: send_message(chat_id, "❌ Owner only!")
            else:
                msg = text.replace("/broadcast","").strip()
                if not msg: send_message(chat_id, "Usage: /broadcast <message>")
                else:
                    c=0
                    for uid in list(USERS):
                        try: 
                            requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": uid, "text": f"📢 <b>Broadcast:</b>\n\n{msg}", "parse_mode":"HTML"}, timeout=5)
                            c+=1
                        except: pass
                    send_message(chat_id, f"✅ Broadcast {c} users ko bhej diya!")
            return "ok",200
        if text.startswith("/start"):
            welcome = "👑 <b>Welcome Owner!</b>\n\n" if is_owner else ""
            full = welcome + START_TEXT + f"\n\n{random.choice(CHAT_STYLE)}"
            try: requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": START_PHOTO, "caption": full, "parse_mode":"HTML"}, timeout=10)
            except: send_message(chat_id, full)
            return "ok",200
        if text.startswith("/help"):
            send_message(chat_id, "❓ <b>Help</b>\nBas Instagram ka link bhej de, main video/photo download karke bhej dunga!\n\nCommands: /start /id /ping /stats")
            return "ok",200

        m = re.search(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not m: return "ok",200
        url = m.group(0)
        loading_id = send_message(chat_id, "⏳ Fetching... 🤖")
        info = download_insta(url)
        if loading_id: delete_message(chat_id, loading_id)
        uploader = info.get('uploader','Insta')
        cap = f"👤 @{uploader}\n\n{info.get('caption','')[:800]}" if info.get('caption') else f"👤 @{uploader}"
        if info['type'] in ['photo','carousel']:
            for i, img in enumerate(info.get('images',[])[:10]): send_photo(chat_id, img, cap if i==0 else "")
        else:
            vurl = info.get('url') or (info.get('formats',[{}])[-1].get('url'))
            if vurl: send_video(chat_id, vurl, cap)
    except Exception as e:
        print(e)
        if loading_id:
            try: delete_message(request.get_json()["message"]["chat"]["id"], loading_id)
            except: pass
    return "ok",200
