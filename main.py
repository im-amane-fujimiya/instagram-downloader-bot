from flask import Flask, request
import re, os
import config
from api.supabase import register_chat, get_all_chats, add_stat, get_stats_count
from api.telegram import send_message
from extractor.instagram import download_insta
from metadata.parser import build_caption
from media.handler import handle_media_sending
from cleanup import cleanup_temp

app = Flask(__name__)
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")

@app.route("/", methods=["GET"])
def home(): return "Bot Alive - Full Structure ✅"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data: return "ok", 200
    msg = data.get("message") or data.get("channel_post")
    if not msg: return "ok", 200

    chat_id = msg["chat"]["id"]
    text = msg.get("text","")
    register_chat(chat_id)

    if text.startswith("/start"): send_message(chat_id, config.START_MSG)
    elif text.startswith("/help"): send_message(chat_id, config.HELP_MSG)
    elif text.startswith("/ping"): send_message(chat_id, config.PING_MSG)
    elif text.startswith("/stats"):
        count = get_stats_count()
        send_message(chat_id, f"📊 **Stats:**\nTotal Downloads: {count}")
    elif text.startswith("/broadcast"):
        if str(chat_id)!= str(OWNER_CHAT_ID):
            send_message(chat_id, "Sirf Malik ke liye hai!"); return "ok", 200
        b_msg = text.replace("/broadcast","").strip()
        if not b_msg: send_message(chat_id, "Message likho: /broadcast hello"); return "ok", 200
        chats = get_all_chats()
        send_message(chat_id, f"Broadcasting to {len(chats)}...")
        for c in chats:
            try: send_message(c, f"📢 {b_msg}")
            except: pass
        send_message(chat_id, "✅ Done!")

    elif "instagram.com" in text:
        link = re.search(r'(https?://[^\s]+)', text).group(1)
        send_message(chat_id, config.DOWNLOADING_MSG)
        files, info, tmpdir = download_insta(link)
        if files and info:
            caption = build_caption(info)
            handle_media_sending(chat_id, files, caption)
            add_stat()
        else:
            send_message(chat_id, config.ERROR_MSG, parse_mode=None)
        cleanup_temp(tmpdir)

    return "ok", 200
