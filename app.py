import sqlite3
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

BOT_TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
ADMIN_ID = 5528758975  # 你的 Telegram 用户 ID
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = "https://telegram-bot-329q.onrender.com" + WEBHOOK_PATH

app = Flask(__name__)
bot = Bot(BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=2, use_context=True)

# --- SQLite数据库相关 ---
def init_db():
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_channel(channel_id):
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO channels (channel_id) VALUES (?)", (str(channel_id),))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("SELECT channel_id FROM channels")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# --- 机器人命令处理 ---
def start(update, context):
    update.message.reply_text("欢迎！本机器人管理员可使用 /broadcast <消息> 向所有频道发送消息。")

def broadcast(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("只有管理员可以使用此命令。")
        return

    text = " ".join(context.args)
    if not text:
        update.message.reply_text("请在 /broadcast 后输入消息内容。")
        return

    channels = get_channels()
    success_count = 0
    fail_count = 0
    for ch_id in channels:
        try:
            bot.send_message(chat_id=ch_id, text=text)
            success_count += 1
        except Exception as e:
            fail_count += 1

    update.message.reply_text(f"消息已发送到 {success_count} 个频道，失败 {fail_count} 个。")

def channel_join(update, context):
    chat = update.effective_chat
    if chat.type in ["channel", "supergroup", "group"]:
        add_channel(chat.id)

# --- 设置命令处理器 ---
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("broadcast", broadcast))
dispatcher.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, channel_join))
dispatcher.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, channel_join))

# --- Flask路由 ---
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running."

if __name__ == "__main__":
    init_db()
    bot.delete_webhook()
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)