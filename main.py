from flask import Flask, request
import telegram
import sqlite3

BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
WEBHOOK_URL = f'https://telegram-bot-329q.onrender.com/{BOT_TOKEN}'

bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)

# 数据库初始化
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

def add_channel(chat_id):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO channels (id) VALUES (?)', (chat_id,))
    conn.commit()
    conn.close()

def get_enabled_channels():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('SELECT id FROM channels WHERE enabled=1')
    channels = [row[0] for row in c.fetchall()]
    conn.close()
    return channels

def disable_channel(chat_id):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('UPDATE channels SET enabled=0 WHERE id=?', (chat_id,))
    conn.commit()
    conn.close()

def get_all_channels():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('SELECT id, enabled FROM channels')
    rows = c.fetchall()
    conn.close()
    return rows

@app.route('/')
def index():
    return 'Bot is running'

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        msg = update.message

        # 如果是频道消息且机器人为管理员，记录频道id
        if msg.chat.type == 'channel':
            add_channel(msg.chat.id)

        # 管理员私聊指令处理
        if msg.chat.type == 'private' and msg.from_user.id == ADMIN_ID:
            if msg.text:
                if msg.text.startswith('/broadcast '):
                    text = msg.text[len('/broadcast '):]
                    for cid in get_enabled_channels():
                        try:
                            bot.send_message(cid, text)
                        except Exception as e:
                            print(f"发送到频道 {cid} 失败：{e}")
                    bot.send_message(ADMIN_ID, '广播完成。')

                elif msg.text.startswith('/channels'):
                    channels = get_all_channels()
                    text = '\n'.join([f'{cid} {"✅" if enabled else "❌"}' for cid, enabled in channels]) or '无记录频道'
                    bot.send_message(ADMIN_ID, text)

                elif msg.text.startswith('/disable_channel '):
                    try:
                        cid = int(msg.text.split(' ')[1])
                        disable_channel(cid)
                        bot.send_message(ADMIN_ID, f'频道 {cid} 已禁用。')
                    except:
                        bot.send_message(ADMIN_ID, '格式错误，用法：/disable_channel 频道ID')

    return 'ok'

@app.route('/setwebhook')
def set_webhook():
    success = bot.set_webhook(WEBHOOK_URL)
    return 'Webhook set!' if success else 'Failed to set webhook.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

