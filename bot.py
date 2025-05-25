import os
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

BOT_TOKEN = os.getenv("BOT_TOKEN", "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://telegram-bot-p5yt.onrender.com/")  # 结尾加斜杠

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("机器人启动成功！")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    port = int(os.environ.get("PORT", "8443"))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL + BOT_TOKEN,
    )

if __name__ == "__main__":
    main()
