from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'  # 频道 ID

# 处理用户发送的消息并直接转发到频道
async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_text = update.message.text  # 获取消息文本
        user_id = update.message.from_user.id  # 获取用户的 ID
        message_id = update.message.message_id  # 获取消息 ID
        chat_id = update.message.chat.id  # 获取聊天 ID（群组或个人）

        # 直接转发用户消息到频道
        try:
            forwarded_message = await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=chat_id,  # 发送者的聊天 ID
                message_id=message_id
            )
            print(f"消息已转发到频道：{CHANNEL_ID}, 消息ID: {forwarded_message.message_id}")
        except Exception as e:
            print(f"转发失败：{str(e)}")
            await update.message.reply_text(f"消息转发失败：{str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 处理所有消息并直接转发
    app.add_handler(MessageHandler(filters.ALL, forward_to_channel))  # 所有用户发送的消息都会直接转发到频道

    print("Bot is running...")
    app.run_polling()
