from flask import Flask, request
import os, requests, re, time

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") or os.getenv("ADMIN_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@Material_01_01"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

START_TEXT = """🎬 <b>Instagram Downloader Bot</b>

🎞 Reels
🎥 Videos
🖼 Photos
📚 Carousels

⚡️ Simple
🎯 Easy to use
🤖 Automated
Built to make saving public Instagram media a little less annoying 😎"""

def sb_headers():
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"} if SUPABASE_KEY else {}

def sb_add_user(chat_id, username="", first_name=""):
    if not SUPABASE_URL or not SUPABASE_KEY: return
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/users", headers={**sb_headers(), "Prefer": "resolution=merge-duplicates"}, json={"chat_id": chat_id, "username": username, "first_name": first_name}, timeout=5)
    except: pass

def send_message(chat_id, text, reply_markup=None):
    try:
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup: data["reply_markup"] = reply_markup
        requests.post(f"{TELEGRAM_API}/sendMessage", json=data, timeout=10)
    except: pass

def download_insta(url):
    try:
        import yt_dlp
        opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get('ext'): 
                return {'type': 'video', 'url': info.get('url') or info['formats'][-1]['url'], 'uploader': info.get('uploader','Insta'), 'caption': info.get('description','')}
    except: pass
    return None

@app.route("/", methods=["GET"])
def home():
    try:
        cmds = [{"command": "start", "description": "🚀 Bot intro"}, {"command": "id", "description": "🆔 ID"}, {"command": "ping", "description": "🏓 Ping"}, {"command": "stats", "description": "📊 Stats"}, {"command": "profile", "description": "👤 DP - /profile username"}, {"command": "help", "description": "❓ Help"}]
        requests.post(f"{TELEGRAM_API}/setMyCommands", json={"commands": cmds}, timeout=5)
    except: pass
    return "MONSTER BOT FIXED 🔥"

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok", 200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        first = data["message"]["from"].get("first_name","")
        user = data["message"]["from"].get("username","")
        is_owner = OWNER_ID and str(chat_id) == str(OWNER_ID)

        sb_add_user(chat_id, user, first)

        if text.startswith("/start"):
            kb = {"inline_keyboard": [[{"text": "📥 Download", "callback_data": "dl"}, {"text": "❓ Help", "callback_data": "help"}], [{"text": f"📢 {CHANNEL_ID}", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}]]}
            msg = f"👑 Welcome Owner!\n\n{START_TEXT}" if is_owner else f"{START_TEXT}\n\n🔥 Bhej de reel, turant laata hu!\n\nChannel: {CHANNEL_ID}"
            try:
                requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": START_PHOTO, "caption": msg, "parse_mode": "HTML", "reply_markup": kb}, timeout=15)
            except:
                send_message(chat_id, msg, kb)
            return "ok",200

        if text.startswith("/id"): send_message(chat_id, f"🆔 <code>{chat_id}</code>"); return "ok",200
        if text.startswith("/ping"): send_message(chat_id, "🏓 Pong! Monster ON hai 🔥"); return "ok",200
        if text.startswith("/help"): send_message(chat_id, f"❓ Link bhej de bas!\n/profile username - DP\nChannel: {CHANNEL_ID}"); return "ok",200

        links = re.findall(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not links: return "ok",200
        
        msg_id = None
        try:
            r = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": "⏳ Fetching... 🤖"}, timeout=10).json()
            msg_id = r.get("result",{}).get("message_id")
        except: pass

        for url in links[:3]:
            info = download_insta(url)
            if msg_id:
                try: requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
                except: pass
            if info and info.get('url'):
                try:
                    requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": info['url'], "caption": f"👤 {info['uploader']}\n\n{info['caption'][:500]}"}, timeout=20)
                    # Channel post
                    try: requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": CHANNEL_ID, "video": info['url'], "caption": f"👤 {info['uploader']}"}, timeout=10)
                    except: pass
                except:
                    send_message(chat_id, f"❌ Download fail: {url}")
            else:
                send_message(chat_id, f"❌ Link samajh nahi aaya: {url[:50]}")
    except Exception as e:
        print("ERR:", e)
    return "ok", 200
