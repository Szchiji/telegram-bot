import os
import sqlite3
from flask import Flask, request
import requests
import json

TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
ADMIN_ID = 5528758975

DATA_DIR = "/tmp/data"
DB_PATH = os.path.join(DATA_DIR, "channels.db")

app = Flask(__name__)
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            channel_title TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels")
    rows = c.fetchall()
    conn.close()
    return rows

def add_channel(channel_id):
    resp = requests.get(f"{API_URL}/getChat", params={"chat_id": channel_id})
    if resp.status_code != 200:
        return False, "无法获取频道信息"
    data = resp.json()
    if not data.get("ok"):
        return False, data.get("description", "添加频道失败")
    title = data["result"].get("title", "未知频道")

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO channels (channel_id, channel_title) VALUES (?, ?)", (channel_id, title))
        conn.commit()
        conn.close()
        return True, title
    except Exception as e:
        return False, str(e)

def del_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
    conn.commit()
    changes = c.rowcount
    conn.close()
    return changes > 0

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=payload)

def forward_message_to_channel(channel_id, from_chat_id, message_id):
    resp = requests.post(f"{API_URL}/forwardMessage", json={
        "chat_id": channel_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
        "disable_notification": True,
    })
    return resp.status_code == 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok"

    # 处理回调查询（按钮点击）
    if "callback_query" in update:
        callback = update["callback_query"]
        data = callback["data"]
        from_id = callback["from"]["id"]
        message_id = callback["message"]["message_id"]
        chat_id = callback["message"]["chat"]["id"]

        if from_id != ADMIN_ID:
            requests.post(f"{API_URL}/answerCallbackQuery", json={
                "callback_query_id": callback["id"],
                "text": "你不是管理员，无权操作",
                "show_alert": True
            })
            return "ok"

        if data.startswith("forward:"):
            _, channel_id, from_chat_id, orig_message_id = data.split(":")
            success = forward_message_to_channel(channel_id, int(from_chat_id), int(orig_message_id))
            answer_text = "转发成功" if success else "转发失败"
            requests.post(f"{API_URL}/answerCallbackQuery", json={
                "callback_query_id": callback["id"],
                "text": answer_text,
                "show_alert": False
            })
            # 删除按钮，避免重复转发
            requests.post(f"{API_URL}/editMessageReplyMarkup", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {}
            })
        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # 仅允许管理员使用机器人，非管理员消息忽略
    if chat_id != ADMIN_ID:
        return "ok"

    from_user = message["from"].get("username") or message["from"].get("first_name") or "用户"

    # 管理员命令处理
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            help_text = (
                "/help - 查看帮助\n"
                "/addchannel <频道ID> - 添加频道，如 -1001234567890\n"
                "/delchannel <频道ID> - 删除频道\n"
                "/list - 查看已添加频道"
            )
            send_message(chat_id, help_text)
            return "ok"

        elif cmd == "/addchannel":
            if not arg:
                send_message(chat_id, "请提供频道ID，例如 /addchannel -1001234567890")
                return "ok"
            ok, msg = add_channel(arg)
            if ok:
                send_message(chat_id, f"成功添加频道：{msg} ({arg})")
            else:
                send_message(chat_id, f"添加失败：{msg}")
            return "ok"

        elif cmd == "/delchannel":
            if not arg:
                send_message(chat_id, "请提供频道ID，例如 /delchannel -1001234567890")
                return "ok"
            ok = del_channel(arg)
            if ok:
                send_message(chat_id, f"已删除频道：{arg}")
            else:
                send_message(chat_id, f"频道不存在或删除失败：{arg}")
            return "ok"

        elif cmd == "/list":
            channels = get_channels()
            if not channels:
                send_message(chat_id, "频道列表为空。")
            else:
                lines = ["已添加频道列表："]
                for cid, title in channels:
                    lines.append(f"{title} ({cid})")
                send_message(chat_id, "\n".join(lines))
            return "ok"

        else:
            send_message(chat_id, "未知命令，请发送 /help 查看帮助。")
            return "ok"

    # 管理员普通消息，回复频道选择按钮
    channels = get_channels()
    if not channels:
        send_message(chat_id, "频道列表为空，请先添加频道。")
        return "ok"
    buttons = []
    for cid, title in channels:
        buttons.append([{
            "text": title,
            "callback_data": f"forward:{cid}:{chat_id}:{message['message_id']}"
        }])
    reply_markup = {"inline_keyboard": buttons}
    send_message(chat_id, "请选择转发的频道：", reply_markup)

    return "ok"

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)