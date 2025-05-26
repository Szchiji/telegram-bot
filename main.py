from flask import Flask, request
import os
import json
from telegram import Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.ext import ApplicationBuilder

# ========= 配置变量 ========= #
TOKEN = os.getenv("TELEGRAM_TOKEN", "替换为你的BotToken")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN", "https://你的-render-域名.onrender.com")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # 替换为你的 Telegram 用户ID
CHANNELS_FILE = "channels.json"
PORT = int(os.environ.get("PORT", 10000))
# ============================ #

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()
dispatcher = application.dispatcher


# ========= 工具函数 ========= #
def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_channels(data):
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========= 管理命令 ========= #
def add_channel(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    if update.message.forward_from_chat:
        channel = update.message.forward_from_chat
        channels = load_channels()
        channels[channel.title] = channel.id
        save_channels(channels)
        update.message.reply_text(f"✅ 自动添加频道：{channel.title}（{channel.id}）")

def list_channels(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    channels = load_channels()
    if not channels:
        update.message.reply_text("暂无频道")
        return
    msg = "\n".join([f"{name}：{chat_id}" for name, chat_id in channels.items()])
    update.message.reply_text(f"已添加频道：\n{msg}")

def delete_channel(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 1:
        update.message.reply_text("用法：/delchannel 频道名")
        return
    name = context.args[0]
    channels = load_channels()
    if name in channels:
        del channels[name]
        save_channels(channels)
        update.message.reply_text(f"已删除频道 {name}")
    else:
        update.message.reply_text("未找到该频道")

# ========= 消息处理 ========= #
def admin_send(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    context.bot_data["cache"] = msg
    channels = load_channels()
    if not channels:
        msg.reply_text("暂无可选频道")
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"send:{chat_id}")] for name, chat_id in channels.items()]
    keyboard.append([InlineKeyboardButton("全部频道", callback_data="send:all")])
    msg.reply_text("请选择发送频道：", reply_markup=InlineKeyboardMarkup(keyboard))

def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    if not context.bot_data.get("cache"):
        query.edit_message_text("⚠️ 找不到要发送的消息")
        return

    original = context.bot_data["cache"]
    target = query.data.split("send:")[1]

    try:
        if target == "all":
            for chat_id in load_channels().values():
                forward_message(original, chat_id)
        else:
            forward_message(original, int(target))
        query.edit_message_text("✅ 发送成功")
    except Exception as e:
        query.edit_message_text(f"❌ 发送失败：{e}")

def forward_message(message, chat_id):
    if message.text:
        bot.send_message(chat_id=chat_id, text=message.text)
    elif message.photo:
        bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, caption=message.caption)
    elif message.video:
        bot.send_video(chat_id=chat_id, video=message.video.file_id, caption=message.caption)

# ========= 注册 Handler ========= #
dispatcher.add_handler(CommandHandler("listchannels", list_channels))
dispatcher.add_handler(CommandHandler("delchannel", delete_channel))
dispatcher.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, add_channel))
dispatcher.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, admin_send))
dispatcher.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, admin_send))
dispatcher.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, admin_send))
dispatcher.add_handler(CallbackQueryHandler(button_handler))

# ========= Webhook 接口 ========= #
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

def set_webhook():
    webhook_url = f"{WEBHOOK_DOMAIN}/{TOKEN}"
    result = bot.set_webhook(url=webhook_url)
    print("Webhook 设置结果:", result)

# ========= 启动 Flask ========= #
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)