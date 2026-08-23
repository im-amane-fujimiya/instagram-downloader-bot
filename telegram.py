import requests, json, os
TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text, parse_mode="Markdown"):
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode: payload["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)
        r.raise_for_status()
    except:
        payload.pop("parse_mode", None)
        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)

def send_video(chat_id, file_path, caption):
    with open(file_path, 'rb') as f:
        requests.post(f"{TELEGRAM_API}/sendVideo", files={'video': f}, data={'chat_id': chat_id, 'caption': caption[:900], 'parse_mode': 'Markdown'}, timeout=60)

def send_photo(chat_id, file_path, caption):
    with open(file_path, 'rb') as f:
        requests.post(f"{TELEGRAM_API}/sendPhoto", files={'photo': f}, data={'chat_id': chat_id, 'caption': caption[:900], 'parse_mode': 'Markdown'}, timeout=60)
