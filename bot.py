from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import json

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
ADMIN_IDS = [7848870377]  # 管理员的用户 ID

# 存储频道 ID 的文件路径
CHANNEL_ID_FILE = 'channel_id.json'


# 从文件加载频道 ID
def load_channel_id():
    try:
        with open(CHANNEL_ID_FILE, 'r') as f:
            data = json.load(f)
            return data.get('channel_id', None)
    except FileNotFoundError:
        return None


# 保存频道 ID 到文件
def save_channel_id(channel_id):
    with open(CHANNEL_ID_FILE, 'w') as f:
        json.dump({'channel_id': channel_id}, f)


# 处理设置频道命令
async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 仅允许管理员使用该命令
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("你没有权限使用此命令。")
        return

    if context.args:
        new_channel_id = context.args[0]  # 获取频道 ID
        save_channel_id(new_channel_id)  # 保存新的频道 ID
        await update.message.reply_text(f"转发的频道已更换为 {new_channel_id}")
    else:
        await update.message.reply_text("请提供新的频道 ID，例如：/setchannel @new_channel")


# 处理用户发送的消息，转发到当前设置的频道
async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 获取当前设置的频道 ID
    channel_id = load_channel_id()
    if channel_id is None:
        await update.message.reply_text("当前未设置转发的频道。请管理员使用 /setchannel 命令设置一个频道。")
        return

    # 根据消息类型处理转发
    if update.message.text:
        await context.bot.send_message(chat_id=channel_id, text=update.message.text)
        print(f"文本消息已转发到频道：{channel_id}")

    elif update.message.photo:
        photo = update.message.photo[-1]  # 获取最大分辨率的照片
        await context.bot.send_photo(chat_id=channel_id, photo=photo.file_id)
        print(f"照片消息已转发到频道：{channel_id}")

    elif update.message.video:
        video = update.message.video.file_id  # 获取视频文件 ID
        await context.bot.send_video(chat_id=channel_id, video=video)
        print(f"视频消息已转发到频道：{channel_id}")

    else:
        print(f"收到无法处理的消息类型：{type(update.message)}")


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 添加管理员设置频道的命令
    app.add_handler(CommandHandler("setchannel", set_channel))

    # 处理所有消息并转发到当前设置的频道
    app.add_handler(MessageHandler(filters.ALL, forward_to_channel))

    print("Bot is running...")
    app.run_polling()

