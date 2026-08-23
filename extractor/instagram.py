from flask import Flask, request
import os, requests, re, time
from extractor.instagram import download_insta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") or os.getenv("ADMIN_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
START_TIME = time.time()
TOTAL_REQUESTS = 0

def send_message(chat_id, text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10).json()
        if r.get("ok"): return r["result"]["message_id"]
    except: pass
    return None

def delete_message(chat_id, msg_id):
    if not msg_id: return
    try: requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
    except: pass

def send_video(chat_id, url, cap=""):
    requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": url, "caption": cap[:1024]}, timeout=20)

def send_photo(chat_id, url, cap=""):
    requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": url, "caption": cap[:1024]}, timeout=20)

@app.route("/", methods=["GET"])
def home(): return "Bot is running! 👑"

@app.route("/", methods=["POST"])
def webhook():
    global TOTAL_REQUESTS
    loading_id = None
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")

        is_owner = OWNER_ID and str(chat_id).strip() == str(OWNER_ID).strip()

        # /id - Teri ID
        if text == "/id":
            send_message(chat_id, f"🆔 ID: <code>{chat_id}</code>\nOwner ENV: <code>{OWNER_ID}</code>\nOwner: {is_owner}")
            return "ok",200

        # /ping - Bot alive hai ya nahi
        if text == "/ping":
            uptime = int(time.time() - START_TIME)
            send_message(chat_id, f"🏓 Pong! {uptime}s up\n✅ Bot is alive")
            return "ok",200

        # /stats - Owner ke liye
        if text == "/stats":
            if not is_owner:
                send_message(chat_id, "❌ Ye sirf owner ke liye hai")
                return "ok",200
            uptime = int(time.time() - START_TIME)//60
            send_message(chat_id, f"📊 Stats\nUptime: {uptime}m\nTotal Requests: {TOTAL_REQUESTS}\nOwner: {OWNER_ID}")
            return "ok",200

        if text.startswith("/start"):
            msg = f"👑 Welcome Owner {chat_id}!" if is_owner else "👋 Link bhej de!"
            send_message(chat_id, msg + "\n\nCommands:\n/id - apni ID dekho\n/ping - bot check\n/stats - owner stats")
            return "ok",200

        m = re.search(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not m:
            send_message(chat_id, "❌ Sahi Insta link bhej yaar.")
            return "ok",200

        url = m.group(0)
        TOTAL_REQUESTS += 1
        loading_id = send_message(chat_id, "⏳ Fetching...")

        info = download_insta(url)

        # AUTO DELETE - loading msg delete
        if loading_id:
            delete_message(chat_id, loading_id)

        uploader = info.get('uploader','Instagram')
        caption_text = info.get('caption') or info.get('title') or ""
        final_caption = f"👤 @{uploader}"
        if caption_text:
            final_caption += f"\n\n{caption_text[:800]}"

        if info['type'] in ['photo','carousel']:
            for i, img in enumerate(info.get('images',[])[:10]):
                send_photo(chat_id, img, final_caption if i==0 else "")
        else:
            video_url = info.get('url') or (info.get('formats', [{}])[-1].get('url'))
            if not video_url and 'entries' in info: video_url = info['entries'][0].get('url')
            if video_url:
                send_video(chat_id, video_url, final_caption)

    except Exception as e:
        print(f"ERROR {e}")
        if loading_id:
            try: delete_message(request.get_json()["message"]["chat"]["id"], loading_id)
            except: pass
    return "ok",200
