from flask import Flask, request
import telegram
import sqlite3
import os

BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
WEBHOOK_URL = f'https://telegram-bot-329q.onrender.com/{BOT_TOKEN}'

bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)

# 初始化数据库
def init_db():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY,
        name TEXT,
        enabled INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()

init_db()

def add_channel(chat_id, chat_name):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    # 如果频道已存在，只更新名称
    c.execute('SELECT id FROM channels WHERE id=?', (chat_id,))
    if c.fetchone():
        c.execute('UPDATE channels SET name=? WHERE id=?', (chat_name, chat_id))
    else:
        c.execute('INSERT INTO channels (id, name) VALUES (?, ?)', (chat_id, chat_name))
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

def enable_channel(chat_id):
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('UPDATE channels SET enabled=1 WHERE id=?', (chat_id,))
    conn.commit()
    conn.close()

def get_all_channels():
    conn = sqlite3.connect('channels.db')
    c = conn.cursor()
    c.execute('SELECT id, name, enabled FROM channels')
    rows = c.fetchall()
    conn.close()
    return rows

@app.route('/')
def index():
    return 'Bot is running'

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    # 监听机器人状态变化事件，自动记录频道
    if update.my_chat_member:
        chat = update.my_chat_member.chat
        new_status = update.my_chat_member.new_chat_member.status
        if chat.type == 'channel' and new_status in ['administrator', 'member']:
            add_channel(chat.id, chat.title or '')

    # 处理管理员命令
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
                    msg_text = '\n'.join(f'{name or "未知名称"} ({cid}) {"✅" if enabled else "❌"}' for cid, name, enabled in channels)
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

            elif text.startswith('/enable_channel '):
                try:
                    cid = int(text.split(' ')[1])
                    enable_channel(cid)
                    bot.send_message(ADMIN_ID, f'频道 {cid} 已恢复启用。')
                except:
                    bot.send_message(ADMIN_ID, '命令格式错误，示例：/enable_channel 频道ID')

            elif text == '/help':
                help_text = (
                    "机器人管理员命令说明：\n"
                    "/broadcast 内容 - 广播消息到所有启用频道\n"
                    "/channels - 查看已记录频道及状态\n"
                    "/disable_channel 频道ID - 禁用某频道\n"
                    "/enable_channel 频道ID - 启用某频道\n"
                    "/help - 显示本帮助信息"
                )
                bot.send_message(ADMIN_ID, help_text)

    return 'ok'

@app.route('/setwebhook')
def set_webhook():
    success = bot.set_webhook(WEBHOOK_URL, allowed_updates=["message", "my_chat_member"])
    return 'Webhook 设置成功!' if success else 'Webhook 设置失败!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
