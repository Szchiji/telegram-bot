import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158

# /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "欢迎使用投稿 Bot！\n\n"
        "您发送的消息将匿名发布到频道。"
    )
    await update.message.reply_text(msg)

# 用户发送文本 → 直接转发到频道
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=update.message.text)
        await update.message.reply_text("您的消息已匿名发布到频道。")

# 设置 Webhook
async def set_webhook(app):
    await app.bot.set_webhook("https://telegram-bot-g6id.onrender.com/webhook")

# 启动函数
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_path="/webhook",
        on_startup=set_webhook
    )

if __name__ == "__main__":
    main()
