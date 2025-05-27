import os
import sqlite3
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from telegram.utils.request import Request

# === 配置信息 ===
TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975

# === Flask 初始化 ===
app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=2, use_context=True)

# === 数据库 ===
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def add_channel(channel_id):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO channels (channel_id) VALUES (?)', (str(channel_id),))
        conn.commit()
    except Exception as e:
        print(f"添加频道失败: {e}")
    finally:
        conn.close()

def get_channels():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# === 命令处理 ===
def send_command(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("你没有权限使用此命令。")
        return

    message_text = ' '.join(context.args)
    if not message_text:
        update.message.reply_text("请提供要发送的内容。格式：/send 你的内容")
        return

    channels = get_channels()
    success, fail = 0, 0
    for cid in channels:
        try:
            bot.send_message(chat_id=cid, text=message_text)
            success += 1
        except Exception as e:
            print(f"发送失败: {e}")
            fail += 1

    update.message.reply_text(f"发送完成 ✅ 成功: {success}, 失败: {fail}")

# 自动记录频道
def auto_record_channel(update, context):
    chat = update.effective_chat
    if chat.type in ['channel', 'supergroup']:
        add_channel(chat.id)

# === Dispatcher 设置 ===
dispatcher.add_handler(CommandHandler("send", send_command))

# === Webhook 路由 ===
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    if update.message:
        auto_record_channel(update, None)
    dispatcher.process_update(update)
    return 'ok'

# === 启动项 ===
@app.route('/')
def index():
    return "Bot is running."

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
