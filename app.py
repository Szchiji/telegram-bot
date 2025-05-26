import os
import sqlite3
import threading
from flask import Flask, request
import requests

TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
ADMIN_ID = 5528758975

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "channels.db")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# 内存缓存用户消息（线程安全）
message_cache = {}
cache_lock = threading.Lock()

def cache_message(msg_id, from_user, text):
    with cache_lock:
        message_cache[msg_id] = {"from_user": from_user, "text": text}

def pop_message(msg_id):
    with cache_lock:
        return message_cache.pop(msg_id, None)

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
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    resp = requests.post(f"{API_URL}/sendMessage", json=data)
    print(f"send_message to {chat_id}, status: {resp.status_code}")
    return resp.status_code == 200

def forward_to_channel(channel_id, text, from_user):
    send_text = f"【匿名转发】\n{from_user} 发送:\n\n{text}"
    r = requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": channel_id,
        "text": send_text,
        "parse_mode": "HTML"
    })
    print(f"forward_to_channel {channel_id} status: {r.status_code}")
    return r.status_code == 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("收到更新:", update)

    if not update:
        return "ok"

    callback_query = update.get("callback_query")
    if callback_query:
        from_user_id = callback_query["from"]["id"]
        if from_user_id != ADMIN_ID:
            # 非管理员操作回绝
            return "ok"

        data = callback_query.get("data", "")
        if data.startswith("sendto:"):
            # 格式 sendto:<channel_id>:<msg_id>
            parts = data.split(":")
            if len(parts) == 3:
                _, channel_id, msg_id = parts
                cached = pop_message(msg_id)
                if not cached:
                    requests.post(f"{API_URL}/answerCallbackQuery", json={
                        "callback_query_id": callback_query["id"],
                        "text": "消息已过期或不存在",
                        "show_alert": True
                    })
                    return "ok"
                ok = forward_to_channel(channel_id, cached["text"], cached["from_user"])
                answer_text = "发送成功" if ok else "发送失败"
                requests.post(f"{API_URL}/answerCallbackQuery", json={
                    "callback_query_id": callback_query["id"],
                    "text": answer_text,
                    "show_alert": False
                })
                send_message(ADMIN_ID, f"消息已转发到频道 {channel_id}，结果：{answer_text}")
            return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    from_user = message["from"].get("username") or message["from"].get("first_name") or "用户"
    text = message.get("text", "")

    # 管理员命令处理
    if chat_id == ADMIN_ID and text.startswith("/"):
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

    # 普通用户消息处理
    channels = get_channels()
    if not channels:
        send_message(chat_id, "暂无可转发的频道，请联系管理员添加频道。")
        return "ok"

    msg_id = f"{chat_id}_{message['message_id']}"
    cache_message(msg_id, from_user, text)

    buttons = []
    for ch_id, ch_title in channels:
        callback_data = f"sendto:{ch_id}:{msg_id}"
        buttons.append([{"text": ch_title, "callback_data": callback_data}])

    reply_markup = {"inline_keyboard": buttons}
    send_message(ADMIN_ID, f"用户 <b>{from_user}</b> 发送消息，选择转发频道：\n\n{text}", reply_markup=reply_markup)
    send_message(chat_id, "你的消息已收到，管理员会选择转发到频道。")

    return "ok"


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)