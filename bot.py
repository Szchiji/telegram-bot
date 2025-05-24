from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'  # 频道 ID

# 处理用户发送的消息并直接转发到频道，模拟匿名
async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_text = update.message.text  # 获取消息文本

        # 使用机器人发送一条新的消息而不是转发原始消息
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"【匿名消息】\n{message_text}"  # 这里可以修改消息格式为匿名
            )
            print(f"消息已转发到频道：{CHANNEL_ID}")
        except Exception as e:
            print(f"转发失败：{str(e)}")
            await update.message.reply_text(f"消息转发失败：{str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 处理所有消息并模拟匿名转发
    app.add_handler(MessageHandler(filters.ALL, forward_to_channel))  # 所有用户发送的消息都会直接转发到频道

    print("Bot is running...")
    app.run_polling()
