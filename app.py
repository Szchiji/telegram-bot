import os
import sqlite3
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
ADMIN_ID = 5528758975
DB_PATH = "/data/channels.db"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def init_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()


def get_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def add_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO channels (channel_id) VALUES (?)', (str(channel_id),))
    conn.commit()
    conn.close()


def send_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)


@app.route('/')
def index():
    return 'Bot is running.'


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("收到更新:", update)

    if "message" in update:
        msg = update["message"]
        user_id = msg["from"]["id"]
        message_id = msg["message_id"]
        chat_id = msg["chat"]["id"]

        if user_id != ADMIN_ID:
            send_message(chat_id, "你不是管理员，无法使用此机器人。")
            return "ok"

        if "text" in msg:
            text = msg["text"]
            # 缓存消息，发送频道选择按钮
            buttons = []
            channels = get_channels()
            if channels:
                for c in channels:
                    buttons.append([{
                        "text": f"发送到 {c}",
                        "callback_data": f"send|{c}|{text}"
                    }])
                buttons.append([{
                    "text": "发送到所有频道",
                    "callback_data": f"send|ALL|{text}"
                }])
                send_message(chat_id, "选择要发送的频道：", {"inline_keyboard": buttons})
            else:
                send_message(chat_id, "尚未记录任何频道，请先将机器人设为管理员再在频道发一条消息。")
    elif "my_chat_member" in update:
        status = update["my_chat_member"]["new_chat_member"]["status"]
        chat = update["my_chat_member"]["chat"]
        if chat["type"] == "channel" and status == "administrator":
            add_channel(chat["id"])
            print(f"添加频道: {chat['id']}")
    elif "callback_query" in update:
        callback = update["callback_query"]
        data = callback["data"]
        query_id = callback["id"]
        user_id = callback["from"]["id"]
        message_id = callback["message"]["message_id"]
        chat_id = callback["message"]["chat"]["id"]

        if user_id != ADMIN_ID:
            return "ok"

        if data.startswith("send|"):
            _, channel_id, content = data.split("|", 2)
            if channel_id == "ALL":
                for c in get_channels():
                    try:
                        send_message(c, content)
                    except Exception as e:
                        print(f"发送到 {c} 失败: {e}")
            else:
                send_message(channel_id, content)

            requests.post(f"{API_URL}/answerCallbackQuery", json={
                "callback_query_id": query_id,
                "text": "发送完成",
                "show_alert": False
            })

    return "ok"


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)