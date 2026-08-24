from flask import Flask, request
import os, requests
app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
@app.route('/api', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def bot():
    if request.method == "GET":
        return "LIVE 200", 200
    try:
        TOKEN = os.getenv("BOT_TOKEN")
        data = request.get_json(force=True, silent=True)
        if data and "message" in data:
            chat_id = data["message"]["chat"]["id"]
            txt = data["message"].get("text","")
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"Working! You sent: {txt}"}, timeout=10)
    except Exception as e:
        print(e)
    return "ok", 200
