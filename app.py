from flask import Flask, request
import sqlite3
import requests
import os

app = Flask(__name__)

TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'
DB_PATH = 'channels.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO channels (channel_id) VALUES (?)', (channel_id,))
    conn.commit()
    conn.close()

def delete_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE channel_id=?', (channel_id,))
    conn.commit()
    conn.close()

def get_channels():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id FROM channels')
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

def send_message(chat_id, text):
    url = f'{BASE_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

def forward_to_channels(text):
    channels = get_channels()
    for channel_id in channels:
        send_message(channel_id, text)

@app.route('/')
def home():
    init_db()
    return 'Bot is running'

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    init_db()
    data = request.get_json()
    print('收到更新:', data)

    message = data.get('message')
    if not message:
        return 'ok'

    chat_id = message['chat']['id']
    text = message.get('text')

    if not text:
        return 'ok'

    # 管理员命令处理
    if chat_id == ADMIN_ID:
        if text.startswith('/add '):
            channel_id = text.split('/add ')[1]
            add_channel(channel_id)
            send_message(chat_id, f'已添加频道 {channel_id}')
        elif text.startswith('/del '):
            channel_id = text.split('/del ')[1]
            delete_channel(channel_id)
            send_message(chat_id, f'已删除频道 {channel_id}')
        elif text.startswith('/list'):
            channels = get_channels()
            msg = '当前频道列表：\n' + '\n'.join(channels) if channels else '暂无频道'
            send_message(chat_id, msg)
        else:
            forward_to_channels(text)
            send_message(chat_id, '已转发')
    else:
        forward_to_channels(text)

    return 'ok'

# 部署在 Render 时，init_db() 需要在模块加载时执行
init_db()