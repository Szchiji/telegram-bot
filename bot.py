from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'  # 频道 ID

# 处理用户发送的消息，删除原始消息并重新发送
async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_text = update.message.text  # 获取消息文本

        # 删除原始消息
        await update.message.delete()

        # 使用机器人发送一条新的消息，原样转发内容，不带任何标识
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message_text  # 直接发送用户的消息内容
            )
            print(f"消息已转发到频道：{CHANNEL_ID}")
        except Exception as e:
            print(f"转发失败：{str(e)}")
            await update.message.reply_text(f"消息转发失败：{str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 处理所有消息并删除原始消息，直接转发内容
    app.add_handler(MessageHandler(filters.ALL, forward_to_channel))  # 所有用户发送的消息都会直接转发到频道

    print("Bot is running...")
    app.run_polling()

