import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.environ["BOT_TOKEN"]

app = Flask(__name__)

bot_app = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .build()
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text.startswith("http"):
        await update.message.reply_text(
            "🔎 Link received!\n\n"
            "Instagram downloader processing will be added next."
        )
    else:
        await update.message.reply_text(
            "📸 Instagram link bhejo."
        )


bot_app.add_handler(
    MessageHandler(filters.TEXT, handle_message)
)


@app.get("/")
def home():
    return "Instagram Downloader Bot is running!"


@app.post("/webhook")
async def webhook():
    data = request.get_json(force=True)

    update = Update.de_json(
        data,
        bot_app.bot
    )

    await bot_app.process_update(update)

    return "OK"


async def start_bot():
    await bot_app.initialize()
    await bot_app.start()


if __name__ == "__main__":
    import hypercorn.asyncio
    from hypercorn.config import Config

    async def run():
        await start_bot()

        config = Config()
        config.bind = [
            f"0.0.0.0:{os.environ.get('PORT', '10000')}"
        ]

        await hypercorn.asyncio.serve(app, config)

    asyncio.run(run())
