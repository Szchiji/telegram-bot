import os
import sqlite3
from flask import Flask, request, jsonify
import requests

TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"  # 你的机器人 Token
ADMIN_ID = 5528758975  # 管理员 ID

DATA_DIR = "data"  # 相对路径，项目根目录下
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
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=data)

def forward_to_channel(channel_id, text, from_user):
    send_text = f"【匿名转发】\n{from_user} 发送:\n\n{text}"
    r = requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": channel_id,
        "text": send_text,
        "parse_mode": "HTML"
    })
    return r.status_code == 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok"

    message = update.get("message")
    callback_query = update.get("callback_query")

    # 处理按钮回调
    if callback_query:
        from_user_id = callback_query["from"]["id"]
        if from_user_id != ADMIN_ID:
            # 非管理员禁止操作
            return jsonify({"text": "无权限操作"}), 200

        data = callback_query.get("data", "")
        # data格式：sendto:<channel_id>:<original_user>:<message_text>
        if data.startswith("sendto:"):
            parts = data.split(":", 3)
            if len(parts) == 4:
                _, channel_id, from_user, text = parts
                ok = forward_to_channel(channel_id, text, from_user)
                answer_text = "发送成功" if ok else "发送失败"
                # 回复回调
                requests.post(f"{API_URL}/answerCallbackQuery", json={
                    "callback_query_id": callback_query["id"],
                    "text": answer_text,
                    "show_alert": False
                })
                # 同时给管理员发确认消息
                send_message(ADMIN_ID, f"消息已转发到频道 {channel_id}，结果：{answer_text}")
                return "ok"
        return "ok"

    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    from_user = message["from"].get("username") or message["from"].get("first_name") or "用户"
    text = message.get("text", "")

    # 仅管理员可用命令
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

    # 普通用户发送消息，管理员收到选择按钮，管理员点击后转发
    channels = get_channels()
    if not channels:
        send_message(chat_id, "暂无可转发的频道，请联系管理员添加频道。")
        return "ok"

    # 构建选择频道的按钮
    buttons = []
    for ch_id, ch_title in channels:
        # callback_data 格式： sendto:<channel_id>:<from_user>:<text>
        # 注意 text 可能过长或包含特殊字符，需要处理，比如简化或限制长度
        safe_text = text.replace("\n", " ").replace(":", " ").strip()
        if len(safe_text) > 50:
            safe_text = safe_text[:47] + "..."
        callback_data = f"sendto:{ch_id}:{from_user}:{safe_text}"
        buttons.append([{"text": ch_title, "callback_data": callback_data}])

    reply_markup = {"inline_keyboard": buttons}
    send_message(ADMIN_ID, f"用户 <b>{from_user}</b> 发送消息，选择转发频道：\n\n{text}", reply_markup=reply_markup)
    send_message(chat_id, "你的消息已收到，管理员会选择转发到频道。")

    return "ok"


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)