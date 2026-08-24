from flask import Flask, request
import os, requests
import yt_dlp

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
PHOTO = "https://files.catbox.moe/3f7j4v.jpg"

def get_insta_url(insta_link):
    try:
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(insta_link, download=False)
            # Reel ke liye best url
            if 'url' in info: return info['url']
            if 'entries' in info: return info['entries'][0]['url']
            return info.get('webpage_url')
    except Exception as e:
        print(e)
        return None

@app.route('/', methods=['GET','POST'])
@app.route('/api', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def bot():
    if request.method == "GET":
        return "MONSTER V3 LIVE 🔥", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")

        API = f"https://api.telegram.org/bot{TOKEN}"

        if "/start" in text:
            requests.post(f"{API}/sendPhoto", json={
                "chat_id": chat_id,
                "photo": PHOTO,
                "caption": "🔥 <b>MONSTER DOWNLOADER ON!</b>\n\nReel / Photo / Story ka link bhej, direct bhejunga!",
                "parse_mode": "HTML"
            }, timeout=15)
        elif "instagram.com" in text or "instagr.am" in text:
            requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "📥 Downloading... 5 sec!"}, timeout=10)

            video_url = get_insta_url(text.strip())

            if video_url and "http" in video_url:
                requests.post(f"{API}/sendVideo", json={"chat_id": chat_id, "video": video_url, "caption": "✅ Done @Instagram_allinone_bot"}, timeout=30)
            else:
                requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "❌ Link private hai ya galat hai! Public reel bhej!"}, timeout=10)

    except Exception as e:
        print(f"ERROR: {e}")
    return "ok", 200
