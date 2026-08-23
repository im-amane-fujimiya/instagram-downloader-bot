from flask import Flask, request
import os, requests, re
from extractor.instagram import download_insta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") or os.getenv("ADMIN_ID") or os.getenv("OWNER")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10).json()
        if r.get("ok"):
            return r["result"]["message_id"]
    except: pass
    return None

def delete_message(chat_id, msg_id):
    if not msg_id: return
    try:
        requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
    except: pass

def send_video(chat_id, video_url, caption=""):
    requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": video_url, "caption": caption[:1024]}, timeout=20)

def send_photo(chat_id, photo_url, caption=""):
    requests.post(f"{TELEGRAM_API}/sendPhoto", json={"chat_id": chat_id, "photo": photo_url, "caption": caption[:1024]}, timeout=20)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

@app.route("/", methods=["POST"])
def webhook():
    loading_id = None
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text","")

        is_owner = False
        if OWNER_ID and str(chat_id).strip() == str(OWNER_ID).strip():
            is_owner = True

        if text == "/id":
            send_message(chat_id, f"🆔 Teri ID: <code>{chat_id}</code>\nOwner ENV: <code>{OWNER_ID}</code>\nOwner hai: {is_owner}")
            return "ok",200

        if text.startswith("/start"):
            if is_owner:
                send_message(chat_id, f"👑 Welcome Owner! <code>{chat_id}</code>")
            else:
                send_message(chat_id, "👋 Link bhej de!")
            return "ok",200

        m = re.search(r'https?://(?:www\.)?instagram\.com/[^\s]+', text)
        if not m:
            send_message(chat_id, "❌ Sahi link bhej.")
            return "ok",200

        url = m.group(0)
        loading_id = send_message(chat_id, "⏳ Fetching...")
        info = download_insta(url)
        if loading_id:
            delete_message(chat_id, loading_id)

        uploader = info.get('uploader','Instagram')
        caption_text = info.get('caption') or info.get('title') or ""
        final_caption = f"👤 @{uploader}\n\n{caption_text[:800]}" if caption_text else f"👤 @{uploader}"

        if info['type'] in ['photo','carousel']:
            for i, img in enumerate(info.get('images',[])[:10]):
                cap = final_caption if i==0 else ""
                send_photo(chat_id, img, cap)
        else:
            video_url = info.get('url') or (info.get('formats', [{}])[-1].get('url'))
            if not video_url and 'entries' in info:
                video_url = info['entries'][0].get('url')
            if video_url:
                send_video(chat_id, video_url, final_caption)

    except Exception as e:
        print(f"ERROR {e}")
    return "ok",200
