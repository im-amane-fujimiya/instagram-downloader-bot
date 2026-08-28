from flask import Flask, request
import os, requests, re
import yt_dlp
import instaloader

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
PHOTO = "https://files.catbox.moe/3f7j4v.jpg" # Apni photo ka link daal de yaha
L = instaloader.Instaloader()

def save_user(cid, uname, fname):
    try:
        url = f"{S_URL}/rest/v1/users"
        h = {"apikey": S_KEY, "Authorization": f"Bearer {S_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
        requests.post(url, json={"chat_id": cid, "username": uname, "first_name": fname}, headers=h, timeout=10)
    except: pass

@app.route('/', methods=['GET','POST'])
@app.route('/api', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def bot():
    if request.method == "GET":
        return "MONSTER V9 BUTTONS 🔥", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        raw = msg.get("text","").strip()
        low = raw.lower()
        API = f"https://api.telegram.org/bot{TOKEN}"
        user = msg.get("from",{})
        first_name = user.get("first_name","Bhai")

        # --- WELCOME WITH BUTTONS ---
        if low.startswith("/start"):
            save_user(chat_id, user.get("username",""), first_name)
            welcome_text = f"""
🔥 <b>Welcome {first_name}!</b> 🔥

<b>MONSTER Downloader Bot me swagat hai!</b>

📥 <b>Features:</b>
• Instagram Reel Downloader
• Photo Downloader  
• Carousel (10+ Photos/Videos)
• Fast & No Watermark

👇 <b>Bas Instagram ka link bhej de!</b>
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📖 HELP", "callback_data": "help"}, {"text": "👥 STATS", "callback_data": "stats"}],
                    [{"text": "📢 Channel Join Karo", "url": "https://t.me/yourchannel"}], # Yaha apna channel link daal de
                    [{"text": "👨‍💻 Developer", "url": "https://t.me/yourusername"}] # Yaha apna username daal
                ]
            }
            try:
                requests.post(f"{API}/sendPhoto", json={"chat_id":chat_id, "photo":PHOTO, "caption":welcome_text, "parse_mode":"HTML", "reply_markup": keyboard}, timeout=15)
            except:
                requests.post(f"{API}/sendMessage", json={"chat_id":chat_id, "text":welcome_text, "parse_mode":"HTML", "reply_markup": keyboard}, timeout=15)
            return "ok",200

        if low.startswith("/help"):
            help_text = "📖 <b>HELP MENU</b>\n\n1. Instagram ka link copy karo\n2. Yaha bhej do\n3. Bot auto download karke de dega!\n\n<b>Commands:</b>\n/start - Bot start\n/help - Ye menu\n/stats - Total users"
            keyboard = {"inline_keyboard": [[{"text": "🔙 Back to Start", "callback_data": "start"}]]}
            requests.post(f"{API}/sendMessage", json={"chat_id":chat_id, "text":help_text, "parse_mode":"HTML", "reply_markup": keyboard}, timeout=15)
            return "ok",200

        if low.startswith("/stats"):
            h={"apikey":S_KEY, "Authorization": f"Bearer {S_KEY}"}
            r=requests.get(f"{S_URL}/rest/v1/users?select=chat_id", headers=h, timeout=10)
            c=len(r.json()) if r.ok else 0
            requests.post(f"{API}/sendMessage", json={"chat_id":chat_id, "text":f"👥 <b>Total Users:</b> {c}\n\nBot is working fine 🔥", "parse_mode":"HTML"}, timeout=15)
            return "ok",200

        # --- DOWNLOADER SAME AS BEFORE - NO CHANGE ---
        if "instagram.com" in low:
            requests.post(f"{API}/sendMessage", json={"chat_id":chat_id, "text":"📥 Downloading..."}, timeout=10)
            try:
                with yt_dlp.YoutubeDL({'quiet':True, 'no_warnings':True, 'skip_download':True}) as ydl:
                    info=ydl.extract_info(raw, download=False)
                    urls = []
                    if 'entries' in info:
                        for e in info['entries']: urls.append(e.get('url'))
                    else:
                        urls.append(info.get('url'))
                    for u in urls:
                        if u:
                            requests.post(f"{API}/sendVideo", json={"chat_id":chat_id, "video":u}, timeout=40)
                    return "ok",200
            except Exception as e:
                print(f"ytdlp fail: {e}")
                try:
                    m=re.search(r'/(?:p|reel|reels)/([^/]+)/', raw)
                    if not m: raise Exception("No shortcode")
                    shortcode=m.group(1)
                    post=instaloader.Post.from_shortcode(L.context, shortcode)
                    if post.is_video:
                        requests.post(f"{API}/sendVideo", json={"chat_id":chat_id, "video":post.video_url}, timeout=40)
                    else:
                        if post.mediacount>1:
                            for sidecar in post.get_sidecar_nodes():
                                if sidecar.is_video:
                                    requests.post(f"{API}/sendVideo", json={"chat_id":chat_id, "video":sidecar.video_url}, timeout=40)
                                else:
                                    requests.post(f"{API}/sendPhoto", json={"chat_id":chat_id, "photo":sidecar.display_url}, timeout=40)
                        else:
                            requests.post(f"{API}/sendPhoto", json={"chat_id":chat_id, "photo":post.url}, timeout=40)
                    return "ok",200
                except Exception as e2:
                    print(f"insta fail: {e2}")
                    requests.post(f"{API}/sendMessage", json={"chat_id":chat_id, "text":f"❌ Private post hai!\n{e2}"}, timeout=10)
    except Exception as e:
        print(e)
    return "ok",200
