from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'  # 频道 ID

# 处理用户发送的消息，转发消息而不显示原始用户的信息
async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        # 文本消息
        if update.message.text:
            message_text = update.message.text  # 获取消息文本
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message_text  # 直接发送文本消息
            )
            print(f"文本消息已转发到频道：{CHANNEL_ID}")

        # 照片消息
        elif update.message.photo:
            photo = update.message.photo[-1]  # 获取最大分辨率的照片
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo.file_id  # 转发照片
            )
            print(f"照片消息已转发到频道：{CHANNEL_ID}")

        # 视频消息
        elif update.message.video:
            video = update.message.video.file_id  # 获取视频文件 ID
            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=video  # 转发视频
            )
            print(f"视频消息已转发到频道：{CHANNEL_ID}")

        # 其他类型的消息（音频、文件等）
        else:
            print(f"收到无法处理的消息类型：{type(update.message)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 处理所有消息并转发到频道
    app.add_handler(MessageHandler(filters.ALL, forward_to_channel))  # 所有类型的消息都会直接转发到频道

    print("Bot is running...")
    app.run_polling()


