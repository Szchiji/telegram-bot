from flask import Flask, request
import telegram
import sqlite3
import os

# === 配置 ===
BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
WEBHOOK_URL = 'https://telegram-bot-329q.onrender.com'
bot = telegram.Bot(BOT_TOKEN)

# === Flask App ===
app = Flask(__name__)

# === 初始化数据库 ===
def init_db():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === 添加频道记录 ===
def add_channel(chat_id):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO channels (id) VALUES (?)', (chat_id,))
    conn.commit()
    conn.close()

# === 获取启用频道 ===
def get_enabled_channels():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('SELECT id FROM channels WHERE enabled = 1')
    results = [row[0] for row in c.fetchall()]
    conn.close()
    return results

# === 禁用频道 ===
def disable_channel(chat_id):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('UPDATE channels SET enabled = 0 WHERE id = ?', (chat_id,))
    conn.commit()
    conn.close()

# === 获取所有频道 ===
def get_all_channels():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('SELECT id, enabled FROM channels')
    results = c.fetchall()
    conn.close()
    return results

# === 设置 Webhook ===
@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    success = bot.set_webhook(f'{WEBHOOK_URL}')
    return 'Webhook set!' if success else 'Failed to set webhook.'

# === 处理 Telegram 更新 ===
@app.route('/', methods=['POST'])
def handle_update():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        msg = update.message

        # 被添加为频道管理员时记录频道 ID
        if msg.chat.type in ['channel']:
            add_channel(msg.chat.id)

        # 管理员命令：广播消息
        if msg.chat.type == 'private' and msg.from_user.id == ADMIN_ID:
            if msg.text.startswith('/broadcast '):
                content = msg.text.replace('/broadcast ', '', 1)
                for channel_id in get_enabled_channels():
                    try:
                        bot.send_message(chat_id=channel_id, text=content)
                    except Exception as e:
                        print(f'Failed to send to {channel_id}: {e}')
                bot.send_message(chat_id=ADMIN_ID, text="广播完成。")

            elif msg.text.startswith('/channels'):
                data = get_all_channels()
                text = '\n'.join([f'{cid} {"✅" if enabled else "❌"}' for cid, enabled in data]) or "无记录频道"
                bot.send_message(chat_id=ADMIN_ID, text=text)

            elif msg.text.startswith('/disable_channel '):
                try:
                    cid = int(msg.text.split(' ')[1])
                    disable_channel(cid)
                    bot.send_message(chat_id=ADMIN_ID, text=f"频道 {cid} 已禁用。")
                except:
                    bot.send_message(chat_id=ADMIN_ID, text="格式错误。用法：/disable_channel 频道ID")

    return 'ok'
