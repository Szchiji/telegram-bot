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
        enabled INTEGER DEFAULT 1
    )''')
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

    # 监听机器人状态变化事件，自动记录频道和处理退出频道
    if update.my_chat_member:
        chat = update.my_chat_member.chat
        new_status = update.my_chat_member.new_chat_member.status
        # 频道，机器人被加入为成员或管理员时添加
        if chat.type == 'channel':
            if new_status in ['administrator', 'member']:
                add_channel(chat.id)
            # 机器人被踢出或退出频道，删除频道记录（或禁用）
            elif new_status == 'left':
                disable_channel(chat.id)

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
                    msg_lines = []
                    for cid, enabled in channels:
                        if enabled == 1:
                            try:
                                chat = bot.get_chat(cid)
                                name = chat.title or str(cid)
                                msg_lines.append(f'{name}（{cid}） ✅')
                            except Exception:
                                msg_lines.append(f'未知频道（{cid}） ✅')
                        else:
                            msg_lines.append(f'禁用频道（{cid}） ❌')
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

            elif text.startswith('/enable_channel '):
                try:
                    cid = int(text.split(' ')[1])
                    enable_channel(cid)
                    bot.send_message(ADMIN_ID, f'频道 {cid} 已启用。')
                except:
                    bot.send_message(ADMIN_ID, '命令格式错误，示例：/enable_channel 频道ID')

            elif text == '/help':
                help_text = (
                    "/broadcast 消息内容 - 向所有启用的频道广播消息\n"
                    "/channels - 查询所有频道及实时名称和启用状态\n"
                    "/disable_channel 频道ID - 禁用某个频道\n"
                    "/enable_channel 频道ID - 启用某个频道\n"
                    "/help - 显示帮助信息"
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
