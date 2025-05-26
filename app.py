import sqlite3
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_IDS = {5528758975}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, None, workers=0)

DB_PATH = 'channels.db'

# 初始化数据库，创建频道表
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def add_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO channels(channel_id) VALUES(?)', (channel_id,))
    conn.commit()
    conn.close()

def get_all_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# 管理员广播命令
def broadcast(update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("您没有权限执行此命令。")
        return

    text = update.message.text
    parts = text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        update.message.reply_text("请在命令后输入要广播的消息内容。")
        return

    message = parts[1].strip()
    channels = get_all_channels()
    success_count = 0
    fail_count = 0

    for channel_id in channels:
        try:
            bot.send_message(chat_id=channel_id, text=message)
            success_count += 1
        except Exception as e:
            print(f"向频道 {channel_id} 发送消息失败: {e}")
            fail_count += 1

    update.message.reply_text(f"广播完成，成功：{success_count} 个频道，失败：{fail_count} 个频道。")

# 监听频道消息，自动保存频道ID
def channel_post_handler(update, context):
    chat = update.effective_chat
    if chat.type == 'channel':
        add_channel(chat.id)

dp.add_handler(CommandHandler("broadcast", broadcast))
dp.add_handler(MessageHandler(Filters.chat_type.channel, channel_post_handler))

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return 'ok'

if __name__ == '__main__':
    app.run(port=5000)