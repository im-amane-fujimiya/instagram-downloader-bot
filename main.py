from flask import Flask, request
import os, requests, re

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

def sb_add_user(chat_id, username="", first_name=""):
    if not SUPABASE_URL or not SUPABASE_KEY: return
    try:
        h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
        requests.post(f"{SUPABASE_URL}/rest/v1/users", headers={**h, "Prefer": "resolution=merge-duplicates"}, json={"chat_id": chat_id, "username": username, "first_name": first_name}, timeout=5)
    except: pass

def send_msg(chat_id, text, kb=None):
    try:
        d = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if kb: d["reply_markup"] = kb
        requests.post(f"{TELEGRAM_API}/sendMessage", json=d, timeout=10)
    except: pass

@app.route("/", methods=["GET"])
def home():
    try:
        cmds = [{"command": "start", "description": "🚀 Bot intro"}, {"command": "id", "description": "🆔 ID"}, {"command": "ping", "description": "🏓 Ping"}, {"command": "help", "description": "❓ Help"}]
        requests.post(f"{TELEGRAM_API}/setMyCommands", json={"commands": cmds}, timeout=5)
    except: pass
    return "MONSTER V2 RUNNING 🔥"

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        first = data["message"]["from"].get("first_name","")
        username = data["message"]["from"].get("username","")
        is_owner = OWNER_ID and str(chat_id) == str(OWNER_ID)

        sb_add_user(chat_id, username, first)

        if text.startswith("/start"):
            kb = {"inline_keyboard": [[{"text": "📥 Download", "callback_data": "dl"}, {"text": "❓ Help", "callback_data": "help"}], [{"text": f"📢 {CHANNEL_ID}", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}]]}
            msg = f"👑 Welcome Owner!\n\n{START_TEXT}" if is_owner else f"{START_TEXT}\n\n🔥 Bhej de reel!\nChannel: {CHANNEL_ID}"
            try:
                requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": START_PHOTO, "caption": msg, "parse_mode": "HTML", "reply_markup": kb}, timeout=15)
            except:
                send_msg(chat_id, msg, kb)
            return "ok",200

        if text.startswith("/id"): send_msg(chat_id, f"🆔 <code>{chat_id}</code>"); return "ok",200
        if text.startswith("/ping"): send_msg(chat_id, "🏓 Monster ON hai! 500 Gone 🔥"); return "ok",200
        if text.startswith("/help"): send_msg(chat_id, f"Link bhej de bas! Channel: {CHANNEL_ID}"); return "ok",200

        links = re.findall(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not links: return "ok",200

        loading = None
        try:
            r = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": "⏳ Fetching... 🤖"}, timeout=10).json()
            loading = r.get("result",{}).get("message_id")
        except: pass

        for url in links[:3]:
            try:
                import yt_dlp
                ydl_opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    vurl = info.get('url') or (info.get('formats') or [{}])[-1].get('url')
                    cap = info.get('description','')[:500] or f"👤 {info.get('uploader','Insta')}"
                    if vurl:
                        requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": vurl, "caption": cap}, timeout=20)
                        try: requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": CHANNEL_ID, "video": vurl, "caption": cap[:200]}, timeout=10)
                        except: pass
            except Exception as e:
                print(e)
                send_msg(chat_id, f"❌ Download fail, link check kar: {url[:40]}")
            
            if loading:
                try: requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": loading}, timeout=5)
                except: pass
                loading = None

    except Exception as e:
        print("MAIN ERR", e)
    return "ok",200
