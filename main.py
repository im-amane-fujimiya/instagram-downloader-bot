from flask import Flask, request
import os, requests, re, time, random
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") or os.getenv("ADMIN_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@Material_01_01"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_TIME = time.time()

HEADERS = {"User-Agent": "Mozilla/5.0"}
START_PHOTO = "https://files.catbox.moe/3f7j4v.jpg" # India working thumbnail
RATE_LIMIT = {}

START_TEXT = """🎬 <b>Instagram Downloader Bot</b>

🎞 Reels
🎥 Videos
🖼 Photos
📚 Carousels

⚡️ Simple
🎯 Easy to use
🤖 Automated
Built to make saving public Instagram media a little less annoying 😎"""

# --- SUPABASE HELPERS ---
def sb_headers():
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

def sb_add_user(chat_id, username="", first_name=""):
    if not SUPABASE_URL: return
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/users", headers={**sb_headers(), "Prefer": "resolution=merge-duplicates"}, json={"chat_id": chat_id, "username": username, "first_name": first_name}, timeout=5)
        # increment stats
        r = requests.get(f"{SUPABASE_URL}/rest/v1/stats?id=eq.1", headers=sb_headers(), timeout=5).json()
        if r: requests.patch(f"{SUPABASE_URL}/rest/v1/stats?id=eq.1", headers=sb_headers(), json={"total_requests": r[0]['total_requests']+1}, timeout=5)
    except: pass

def sb_get_stats():
    if not SUPABASE_URL: return {"users": 0, "total": 0}
    try:
        u = requests.get(f"{SUPABASE_URL}/rest/v1/users?select=count", headers={**sb_headers(), "Prefer": "count=exact"}, timeout=5).headers.get('content-range','0')
        s = requests.get(f"{SUPABASE_URL}/rest/v1/stats?id=eq.1", headers=sb_headers(), timeout=5).json()
        return {"users": u.split('/')[-1] if '/' in u else 0, "total": s[0]['total_requests'] if s else 0}
    except: return {"users": "Many", "total": "Many"}

def sb_add_download(chat_id, url, dtype):
    if not SUPABASE_URL: return
    try: requests.post(f"{SUPABASE_URL}/rest/v1/downloads", headers=sb_headers(), json={"chat_id": chat_id, "url": url, "type": dtype}, timeout=5)
    except: pass

def sb_get_history(chat_id):
    if not SUPABASE_URL: return []
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/downloads?chat_id=eq.{chat_id}&order=created_at.desc&limit=10", headers=sb_headers(), timeout=5).json()
        return r
    except: return []

def sb_get_all_users():
    if not SUPABASE_URL: return []
    try: return requests.get(f"{SUPABASE_URL}/rest/v1/users?select=chat_id", headers=sb_headers(), timeout=10).json()
    except: return []

# --- TELEGRAM HELPERS ---
def send_message(chat_id, text, reply_markup=None):
    try:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if reply_markup: payload["reply_markup"] = reply_markup
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10).json()
        if r.get("ok"): return r["result"]["message_id"]
    except: pass
    return None

def delete_message(chat_id, msg_id):
    try: requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
    except: pass

def send_video(chat_id, url, cap=""): requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": url, "caption": cap[:1024]}, timeout=30)
def send_photo(chat_id, url, cap=""): requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": url, "caption": cap[:1024]}, timeout=20)
def send_audio(chat_id, url, cap=""): requests.post(f"{TELEGRAM_API}/sendAudio", json={"chat_id": chat_id, "audio": url, "caption": cap[:1024]}, timeout=30)

def set_commands():
    cmds = [{"command": "start", "description": "🚀 Bot intro + thumbnail"}, {"command": "id", "description": "🆔 Teri ID"}, {"command": "ping", "description": "🏓 Bot status"}, {"command": "stats", "description": "📊 Stats"}, {"command": "profile", "description": "👤 DP download - /profile username"}, {"command": "audio", "description": "🎵 Reel se audio"}, {"command": "history", "description": "📜 Last downloads"}, {"command": "help", "description": "❓ Help"}, {"command": "broadcast", "description": "📢 Owner only"}]
    try: requests.post(f"{TELEGRAM_API}/setMyCommands", json={"commands": cmds}, timeout=5)
    except: pass

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
                info['type'] = 'video'; info['uploader'] = info.get('uploader') or "Instagram"; info['caption'] = info.get('description') or ""; return info
    except: pass
    html = requests.get(url, headers=HEADERS, timeout=15).text
    username, caption = "Instagram", ""
    try:
        m1 = re.search(r'"owner":\{"username":"([^"]+)"', html);
        if m1: username = m1.group(1)
        m2 = re.search(r'"caption":\{"text":"([^"]+)"', html);
        if m2: caption = m2.group(1)[:800]
    except: pass
    m = re.search(r'"video_url":"([^"]+)"', html)
    if m: return {'type': 'video', 'url': clean_url(m.group(1)), 'uploader': username, 'caption': caption, 'formats': [{'url': clean_url(m.group(1))}]}
    raw = re.findall(r'"display_url":"([^"]+)"', html); imgs=[]
    for u in raw:
        cu = clean_url(u)
        if cu not in imgs and 's150x150' not in cu: imgs.append(cu)
    return {'type': 'carousel' if len(imgs)>1 else 'photo', 'images': imgs[:10], 'uploader': username, 'caption': caption}

def get_profile(username):
    try:
        html = requests.get(f"https://www.instagram.com/{username}/", headers=HEADERS, timeout=10).text
        pic = re.search(r'"profile_pic_url_hd":"([^"]+)"', html)
        bio = re.search(r'"biography":"([^"]+)"', html)
        return {"pic": clean_url(pic.group(1)) if pic else None, "bio": bio.group(1)[:500] if bio else "No bio"}
    except: return None

set_commands()

@app.route("/", methods=["GET"])
def home(): return "MONSTER BOT RUNNING 🔥"

@app.route("/", methods=["POST"])
def webhook():
    loading_id = None
    try:
        data = request.get_json()
        # Callback query
        if "callback_query" in data:
            cq = data["callback_query"]; chat_id = cq["message"]["chat"]["id"]; cdata = cq["data"]
            if cdata == "help":
                send_message(chat_id, "❓ <b>Help</b>\n1. Insta link bhej\n2. /profile username - DP\n3. /audio - last reel se audio\n4. /history - last 10 downloads")
            elif cdata == "download":
                send_message(chat_id, "📥 Bas Instagram ka link bhej de bhai!")
            requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=5)
            return "ok",200

        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        first_name = data["message"]["from"].get("first_name","")
        username = data["message"]["from"].get("username","")
        is_owner = OWNER_ID and str(chat_id).strip() == str(OWNER_ID).strip()

        # Anti-spam
        now = time.time()
        if chat_id in RATE_LIMIT and now - RATE_LIMIT[chat_id] < 3 and not is_owner:
            return "ok",200
        RATE_LIMIT[chat_id] = now

        sb_add_user(chat_id, username, first_name)

        if text.startswith("/id"): send_message(chat_id, f"🆔 ID: <code>{chat_id}</code>\n👑 Owner: {is_owner}"); return "ok",200
        if text.startswith("/ping"): up = int(time.time()-START_TIME); send_message(chat_id, f"🏓 <b>Pong!</b>\n⏱ {up//60}m {up%60}s\n🔥 Monster Running"); return "ok",200
        if text.startswith("/stats"):
            s = sb_get_stats(); send_message(chat_id, f"📊 <b>Monster Stats</b>\n👥 Users: {s['users']}\n📥 Total: {s['total']}\n📢 Channel: {CHANNEL_ID}"); return "ok",200
        if text.startswith("/help"): send_message(chat_id, f"❓ <b>Commands</b>\n/start - Intro\n/profile username - HD DP\n/audio - last reel audio\n/history - last downloads\n/batch - 3 links ek saath bhej de\n\n<b>Channel:</b> {CHANNEL_ID}"); return "ok",200
        if text.startswith("/profile"):
            uname = text.replace("/profile","").strip().replace("@","")
            if not uname: send_message(chat_id, "Usage: /profile username"); return "ok",200
            p = get_profile(uname)
            if p and p['pic']: send_photo(chat_id, p['pic'], f"👤 @{uname}\n\n{p['bio']}")
            else: send_message(chat_id, "❌ Profile nahi mila, username public hai na?")
            return "ok",200
        if text.startswith("/history"):
            h = sb_get_history(chat_id)
            if not h: send_message(chat_id, "📜 Koi history nahi!")
            else: send_message(chat_id, "📜 <b>Last 10:</b>\n" + "\n".join([f"{i+1}. {x['type']} - {x['url'][:40]}" for i,x in enumerate(h)]))
            return "ok",200
        if text.startswith("/broadcast"):
            if not is_owner: send_message(chat_id, "❌ Owner only!"); return "ok",200
            msg = text.replace("/broadcast","").strip()
            if not msg: send_message(chat_id, "Usage: /broadcast message"); return "ok",200
            users = sb_get_all_users(); c=0
            for u in users:
                try: requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": u['chat_id'], "text": f"📢 <b>Broadcast:</b>\n\n{msg}", "parse_mode":"HTML"}, timeout=5); c+=1
                except: pass
            send_message(chat_id, f"✅ {c} users ko bhej diya!"); return "ok",200
        if text.startswith("/start"):
            kb = {"inline_keyboard": [[{"text": "📥 Download", "callback_data": "download"}, {"text": "❓ Help", "callback_data": "help"}], [{"text": "📢 Channel", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}]]}
            msg = (f"👑 <b>Welcome Owner!</b>\n\n{START_TEXT}" if is_owner else f"{START_TEXT}\n\n🔥 Bhej de reel, turant laata hu!") + f"\n\n<b>Channel:</b> {CHANNEL_ID}"
            try: requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": START_PHOTO, "caption": msg, "parse_mode": "HTML", "reply_markup": kb}, timeout=10)
            except: send_message(chat_id, msg, kb)
            return "ok",200

        # Batch links
        links = re.findall(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not links: return "ok",200
        if len(links) > 3 and not is_owner: send_message(chat_id, "❌ Max 3 links ek saath (spam rokne ke liye)"); links = links[:3]

        for url in links:
            loading_id = send_message(chat_id, "⏳ Fetching... 🤖")
            info = download_insta(url)
            if loading_id: delete_message(chat_id, loading_id)
            uploader = info.get('uploader','Insta'); cap = f"👤 @{uploader}\n\n{info.get('caption','')[:700]}" if info.get('caption') else f"👤 @{uploader}"
            kb2 = {"inline_keyboard": [[{"text": "🎵 Audio", "callback_data": "download"}, {"text": "📋 Caption Copy", "callback_data": "help"}], [{"text": f"📢 {CHANNEL_ID}", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}]]}
            if info['type'] in ['photo','carousel']:
                for i, img in enumerate(info.get('images',[])[:10]):
                    try: requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": img, "caption": cap if i==0 else "", "reply_markup": kb2 if i==0 else None}, timeout=20)
                    except: pass
            else:
                vurl = info.get('url') or (info.get('formats',[{}])[-1].get('url'))
                if vurl:
                    send_video(chat_id, vurl, cap)
                    # Auto-post to channel
                    try: requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": CHANNEL_ID, "video": vurl, "caption": cap[:1024]}, timeout=10)
                    except: pass
            sb_add_download(chat_id, url, info['type'])
    except Exception as e: print(e)
    return "ok",200
