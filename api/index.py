from flask import Flask, request
import os, requests
import yt_dlp

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

def save_user(chat_id, username, first_name):
    try:
        if not S_URL or not S_KEY: return
        url = f"{S_URL}/rest/v1/users"
        headers = {"apikey": S_KEY, "Authorization": f"Bearer {S_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
        data = {"chat_id": chat_id, "username": username, "first_name": first_name}
        requests.post(url, json=data, headers=headers, timeout=10)
    except Exception as e:
        print(f"Supabase Error: {e}")

def get_insta_url(link):
    try:
        ydl_opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            return info.get('url') or (info['entries'][0]['url'] if 'entries' in info else None)
    except:
        return None

@app.route('/', methods=['GET','POST'])
@app.route('/api', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def bot():
    if request.method == "GET":
        return "MONSTER V4 + SUPABASE LIVE 🔥", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")
        user = data["message"].get("from", {})
        username = user.get("username","")
        first_name = user.get("first_name","")

        API = f"https://api.telegram.org/bot{TOKEN}"

        if "/start" in text:
            save_user(chat_id, username, first_name)
            requests.post(f"{API}/sendPhoto", json={
                "chat_id": chat_id,
                "photo": PHOTO,
                "caption": "🔥 <b>MONSTER DOWNLOADER ON + DB SAVED!</b>\n\nReel link bhej, direct dunga!",
                "parse_mode": "HTML"
            }, timeout=15)

        elif "instagram.com" in text:
            requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "📥 Downloading..."}, timeout=10)
            vurl = get_insta_url(text.strip())
            if vurl:
                requests.post(f"{API}/sendVideo", json={"chat_id": chat_id, "video": vurl, "caption": "✅ @Instagram_allinone_bot"}, timeout=30)
            else:
                requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "❌ Private / Invalid link!"}, timeout=10)

    except Exception as e:
        print(e)
    return "ok", 200
