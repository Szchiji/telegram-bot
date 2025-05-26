import os
import sqlite3
from flask import Flask, request
import requests

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_DIR = os.getenv("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "channels.db")

app = Flask(__name__)
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# 初始化数据库
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

# 获取所有频道
def get_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_title FROM channels")
    rows = c.fetchall()
    conn.close()
    return rows

# 添加频道
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

# 删除频道
def del_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
    conn.commit()
    changes = c.rowcount
    conn.close()
    return changes > 0

# 转发消息
def forward_to_channels(text, from_user):
    channels = get_channels()
    results = []
    for ch_id, ch_title in channels:
        try:
            send_text = f"【匿名转发】\n{from_user} 发送:\n\n{text}"
            r = requests.post(f"{API_URL}/sendMessage", json={
                "chat_id": ch_id,
                "text": send_text,
                "parse_mode": "HTML"
            })
            results.append((ch_id, r.status_code == 200))
        except:
            results.append((ch_id, False))
    return results

# 设置 Webhook 路由为 /<TOKEN>
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    from_user = message["from"].get("username") or message["from"].get("first_name") or "用户"

    text = message.get("text", "")
    if not text:
        return "ok"

    if chat_id == ADMIN_ID and text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            send_message(chat_id,
                "/help - 查看帮助\n"
                "/addchannel <频道ID> - 添加频道，如 -1001234567890\n"
                "/delchannel <频道ID> - 删除频道\n"
                "/list - 查看已添加频道"
            )
            return "ok"

        elif cmd == "/addchannel":
            if not arg:
                send_message(chat_id, "请提供频道ID，例如 /addchannel -1001234567890")
                return "ok"
            ok, msg = add_channel(arg)
            send_message(chat_id, f"添加成功：{msg} ({arg})" if ok else f"添加失败：{msg}")
            return "ok"

        elif cmd == "/delchannel":
            if not arg:
                send_message(chat_id, "请提供频道ID，例如 /delchannel -1001234567890")
                return "ok"
            ok = del_channel(arg)
            send_message(chat_id, f"已删除频道：{arg}" if ok else f"频道不存在或删除失败：{arg}")
            return "ok"

        elif cmd == "/list":
            channels = get_channels()
            if not channels:
                send_message(chat_id, "频道列表为空。")
            else:
                msg = "已添加频道列表：\n" + "\n".join(f"{title} ({cid})" for cid, title in channels)
                send_message(chat_id, msg)
            return "ok"

        else:
            send_message(chat_id, "未知命令，请发送 /help 查看帮助。")
            return "ok"

    # 普通用户消息转发
    forward_results = forward_to_channels(text, from_user)
    ok_count = sum(1 for _, ok in forward_results if ok)
    fail_count = len(forward_results) - ok_count
    send_message(chat_id, f"消息已转发到 {ok_count} 个频道，失败 {fail_count} 个频道。")

    return "ok"

# 发送消息工具函数
def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)