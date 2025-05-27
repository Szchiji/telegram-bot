from flask import Flask, request
import telegram
import sqlite3
import os

# 基本配置
BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
WEBHOOK_URL = f'https://telegram-bot-329q.onrender.com/{BOT_TOKEN}'

bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)

# 初始化数据库
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

# 数据库操作函数
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
    res = [row[0] for row in c.fetchall()]
    conn.close()
    return res

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

# 根路由
@app.route('/')
def index():
    return 'Bot is running'

# 设置 Webhook
@app.route('/setwebhook')
def set_webhook():
    success = bot.set_webhook(WEBHOOK_URL, allowed_updates=["message", "my_chat_member"])
    return 'Webhook 设置成功!' if success else 'Webhook 设置失败!'

# Webhook 接收入口
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    # 自动记录频道
    if update.my_chat_member:
        chat = update.my_chat_member.chat
        new_status = update.my_chat_member.new_chat_member.status
        if chat.type == 'channel' and new_status in ['administrator', 'member']:
            add_channel(chat.id)

    # 管理员命令处理
    if update.message:
        msg = update.message
        if msg.chat.type == 'private' and msg.from_user.id == ADMIN_ID:
            text = msg.text or ''
            if text.startswith('/broadcast '):
                broadcast_text = text[len('/broadcast '):]
                count = 0
                for cid in get_enabled_channels():
                    try:
                        bot.send_message(cid, broadcast_text)
                        count += 1
                    except Exception as e:
                        print(f'发送到频道 {cid} 失败: {e}')
                bot.send_message(ADMIN_ID, f'广播完成，发送到 {count} 个频道。')

            elif text == '/channels':
                channels = get_all_channels()
                if channels:
                    msg_lines = []
                    for cid, enabled in channels:
                        try:
                            chat = bot.get_chat(cid)
                            title = chat.title or "无标题"
                        except Exception as e:
                            title = f"获取失败（{e}）"
                        msg_lines.append(f'{cid} | {title} {"✅" if enabled else "❌"}')
                    msg_text = '\n'.join(msg_lines)
                else:
                    msg_text = '无记录频道'
                bot.send_message(ADMIN_ID, msg_text)

            elif text.startswith('/disable_channel '):
                try:
                    cid = int(text.split(' ')[1])
                    disable_channel(cid)
                    bot.send_message(ADMIN_ID, f'频道 {cid} 已禁用。')
                except:
                    bot.send_message(ADMIN_ID, '命令格式错误，示例：/disable_channel 频道ID')

    return 'ok'

# 启动服务
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


