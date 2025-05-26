from flask import Flask, request
import requests
import sqlite3
import os

app = Flask(__name__)

# === 配置区 ===
TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975  # 管理员 Telegram 用户 ID
WEBHOOK_URL = f'https://telegram-bot-nkal.onrender.com/{TOKEN}'

DB_PATH = '/mnt/data/channels.db'

# === 数据库初始化 ===
def init_db():
    os.makedirs('/mnt/data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

def add_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO channels (channel_id) VALUES (?)', (channel_id,))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# === 转发功能 ===
def send_channel_choice(chat_id, msg):
    channels = get_channels()
    if not channels:
        requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', json={
            'chat_id': chat_id,
            'text': '暂无可用频道，请先向频道发送一条消息以授权机器人。'
        })
        return

    buttons = [[{'text': str(cid), 'callback_data': f'{cid}|{msg["message_id"]}'}] for cid in channels]
    requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', json={
        'chat_id': chat_id,
        'text': '请选择要转发的频道：',
        'reply_markup': {'inline_keyboard': buttons}
    })

def forward_to_channel(channel_id, msg):
    if 'text' in msg:
        text = msg['text']
        requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', json={
            'chat_id': channel_id,
            'text': text
        })
    elif 'photo' in msg:
        requests.post(f'https://api.telegram.org/bot{TOKEN}/sendPhoto', json={
            'chat_id': channel_id,
            'photo': msg['photo'][-1]['file_id'],
            'caption': msg.get('caption', '')
        })
    elif 'video' in msg:
        requests.post(f'https://api.telegram.org/bot{TOKEN}/sendVideo', json={
            'chat_id': channel_id,
            'video': msg['video']['file_id'],
            'caption': msg.get('caption', '')
        })

# === Webhook 接收消息 ===
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    init_db()
    data = request.get_json()
    print('收到更新:', data)

    if 'message' in data:
        msg = data['message']
        user_id = msg['from']['id']

        # 如果是频道消息，记录频道 ID
        if msg['chat']['type'] == 'channel':
            add_channel(msg['chat']['id'])
            return 'OK'

        # 管理员发送私聊消息，弹出频道选择
        if user_id == ADMIN_ID and msg['chat']['type'] == 'private':
            send_channel_choice(msg['chat']['id'], msg)
    
    elif 'callback_query' in data:
        query = data['callback_query']
        chat_id = query['message']['chat']['id']
        msg_id = int(query['data'].split('|')[1])
        channel_id = int(query['data'].split('|')[0])
        original_msg = requests.get(
            f'https://api.telegram.org/bot{TOKEN}/getMessage',
            params={'chat_id': chat_id, 'message_id': msg_id}
        ).json()
        if 'result' in original_msg:
            forward_to_channel(channel_id, original_msg['result'])

        # 回答回调
        requests.post(f'https://api.telegram.org/bot{TOKEN}/answerCallbackQuery', json={
            'callback_query_id': query['id'],
            'text': '已转发'
        })

    return 'OK'

# === 设置 Webhook（仅首次部署后访问一次） ===
@app.route('/set_webhook')
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, data={'url': WEBHOOK_URL})
    return response.text

# === 首页检查 ===
@app.route('/')
def index():
    return 'Bot 正在运行...'

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)