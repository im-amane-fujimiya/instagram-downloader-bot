import requests, os
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

def get_headers():
    return {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}

def register_chat(chat_id):
    try:
        r = requests.post(f"{URL}/rest/v1/broadcast_chats", headers=get_headers(), json={"chat_id": str(chat_id)}, timeout=10)
        print(f"BROADCAST REGISTER: {r.status_code}")
        return r.status_code
    except: return 500

def get_all_chats():
    try:
        r = requests.get(f"{URL}/rest/v1/broadcast_chats?select=chat_id", headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}, timeout=10)
        return [x['chat_id'] for x in r.json()]
    except: return []

def add_stat():
    try: requests.post(f"{URL}/rest/v1/bot_stats", headers=get_headers(), json={"event": "download"}, timeout=5)
    except: pass

def get_stats_count():
    try:
        r = requests.get(f"{URL}/rest/v1/bot_stats?select=count", headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}, timeout=5)
        return len(r.json())
    except: return 0
