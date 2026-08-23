import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")

START_MSG = "🔥 **Arey Shan Bhai, Aa Gaye!**\n\nMain hu tera full power downloader, bina watermark ke! 😎\nLink bhej bas!"
HELP_MSG = "🤖 /start - Start\n📥 Insta link bhej - Download\n📊 /stats - Stats\n📢 /broadcast - Broadcast (Owner)\n🏓 /ping - Check Alive"
DOWNLOADING_MSG = "⚡ **Ruko zara...** Reel ka tadka lag raha hai! 🍳"
ERROR_MSG = "😵 Link kharab hai ya private hai!"
PING_MSG = "🏓 Pong! Bot ekdum zinda hai ✅"
