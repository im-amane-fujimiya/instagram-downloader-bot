import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")

START_MSG = "🔥 **Hey! Welcome!**\n\nMain hu tera Insta Downloader Bot, bina watermark ke! 😎\nBas link bhej de."

HELP_MSG = "🤖 /start - Start\n📥 Insta link bhej - Download\n📊 /stats - Stats\n🏓 /ping - Check Alive"

DOWNLOADING_MSG = "⚡ **Ruko zara...** Download ho raha hai! 🍳"
ERROR_MSG = "😵 Link kharab hai ya private hai!"
PING_MSG = "🏓 Pong! Bot Alive ✅"
