import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
WEBHOOK_DOMAIN = "telegram-bot-p5yt.onrender.com"  # 不带 https://
WEBHOOK_PATH = f"/bot{BOT_TOKEN}"
WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用Bot，已成功连接Webhook！")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    await app.bot.set_webhook(WEBHOOK_URL)

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=WEBHOOK_URL,
        webhook_path=WEBHOOK_PATH,
    )

if __name__ == "__main__":
    asyncio.run(main())
