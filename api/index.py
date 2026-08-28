from flask import Flask, request
import os, requests
import yt_dlp

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

def save_user(cid, uname, fname):
    try:
        if not S_URL or not S_KEY: return
        url = f"{S_URL}/rest/v1/users"
        headers = {"apikey": S_KEY, "Authorization": f"Bearer {S_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
        requests.post(url, json={"chat_id": cid, "username": uname, "first_name": fname}, headers=headers, timeout=10)
    except: pass

@app.route('/', methods=['GET','POST'])
@app.route('/api', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def bot():
    if request.method == "GET":
        return "MONSTER V6 PHOTO+VIDEO FIXED 🔥", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200

        msg = data["message"]
        chat_id = msg["chat"]["id"]
        raw_text = msg.get("text","").strip()
        text_low = raw_text.lower()
        user = msg.get("from", {})
        API = f"https://api.telegram.org/bot{TOKEN}"

        # --- COMMANDS (100% FIXED) ---
        if text_low.startswith("/start"):
            save_user(chat_id, user.get("username",""), user.get("first_name",""))
            requests.post(f"{API}/sendPhoto", json={"chat_id": chat_id, "photo": PHOTO, "caption": "🔥 <b>MONSTER V6 ON</b>\n\nReel / Photo / Carousel sab download!\n\n/start - Start\n/help - Help\n/stats - Stats", "parse_mode": "HTML"}, timeout=15)
            return "ok", 200

        if text_low.startswith("/help"):
            requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "📖 HELP\n\nInsta link bhej - Reel/Photo dono download kar dunga!\n\n/start - Start\n/help - Help\n/stats - Users"}, timeout=15)
            return "ok", 200

        if text_low.startswith("/stats"):
            try:
                h = {"apikey": S_KEY, "Authorization": f"Bearer {S_KEY}"}
                r = requests.get(f"{S_URL}/rest/v1/users?select=chat_id", headers=h, timeout=10)
                count = len(r.json()) if r.ok else 0
                requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": f"👥 Total Users: {count}"}, timeout=15)
            except:
                requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "Stats error!"}, timeout=15)
            return "ok", 200

        # --- INSTA DOWNLOADER (PHOTO + VIDEO + CAROUSEL) ---
        if "instagram.com" in text_low:
            requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "📥 Downloading..."}, timeout=10)
            try:
                ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(raw_text, download=False)

                    # Carousel hai toh entries hogi
                    entries = info.get('entries') or [info]

                    for item in entries:
                        url = item.get('url') or item.get('webpage_url')
                        # Thumbnail / direct url check
                        direct_url = item.get('url')
                        ext = item.get('ext','')

                        if not direct_url: continue

                        # Photo hai?
                        if ext in ['jpg','jpeg','png','webp'] or 'image' in item.get('format','').lower() or direct_url.endswith(('.jpg','.png','.webp')):
                            requests.post(f"{API}/sendPhoto", json={"chat_id": chat_id, "photo": direct_url}, timeout=30)
                        else:
                            # Video / Reel
                            requests.post(f"{API}/sendVideo", json={"chat_id": chat_id, "video": direct_url}, timeout=40)

                return "ok", 200
            except Exception as e:
                print(f"YTDLP Error: {e}")
                requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": f"❌ Download fail! Private account ho sakta hai.\nError: {e}"}, timeout=10)

    except Exception as e:
        print(e)
    return "ok", 200
