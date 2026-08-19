import os

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .build()
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello!\n\n"
        "Instagram Downloader Bot is online! 🚀\n\n"
        "Instagram ka public Reel/Post link bhejo."
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text.startswith("http"):
        await update.message.reply_text(
            "🔗 Link received!\n\n"
            "Downloader engine abhi setup ho raha hai. 🚀"
        )
    else:
        await update.message.reply_text(
            "📸 Instagram ka public link bhejo."
        )


telegram_app.add_handler(CommandHandler("start", start))

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)


app = FastAPI()


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
async def home():
    return "Instagram Downloader Bot is running!"


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}
