import os
import sqlite3
import requests
from flask import Flask, request

TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
ADMIN_ID = 5528758975
API_URL = f"https://api.telegram.org/bot{TOKEN}"
WEBHOOK_URL = "https://telegram-bot-329q.onrender.com"

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY, title TEXT)")
    conn.commit()
    conn.close()

def add_channel(channel_id, title=""):
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO channels (id, title) VALUES (?, ?)", (channel_id, title))
    conn.commit()
    conn.close()

def remove_channel(channel_id):
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect("channels.db")
    c = conn.cursor()
    c.execute("SELECT id FROM channels")
    rows = c.fetchall()
    channels = {}
    for (cid,) in rows:
        try:
            res = requests.get(f"{API_URL}/getChat", params={"chat_id": cid}).json()
            if res.get("ok"):
                title = res["result"]["title"]
                channels[cid] = title
                c.execute("UPDATE channels SET title = ? WHERE id = ?", (title, cid))
            else:
                if "chat not found" in res.get("description", ""):
                    c.execute("DELETE FROM channels WHERE id = ?", (cid,))
        except:
            continue
    conn.commit()
    conn.close()
    return channels

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

def forward_to_channels(from_user_id, content):
    channels = get_channels()
    for cid in channels:
        data = {"chat_id": cid}
        if "text" in content:
            data["text"] = content["text"]
            data["parse_mode"] = "HTML"
            requests.post(f"{API_URL}/sendMessage", json=data)
        elif "photo" in content:
            photo = content["photo"][-1]["file_id"]
            caption = content.get("caption", "")
            data["photo"] = photo
            data["caption"] = caption
            data["parse_mode"] = "HTML"
            requests.post(f"{API_URL}/sendPhoto", json=data)
        elif "video" in content:
            video = content["video"]["file_id"]
            caption = content.get("caption", "")
            data["video"] = video
            data["caption"] = caption
            data["parse_mode"] = "HTML"
            requests.post(f"{API_URL}/sendVideo", json=data)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if user_id == ADMIN_ID:
            if text.startswith("/add "):
                try:
                    channel_id = int(text.split(" ")[1])
                    add_channel(channel_id)
                    send_message(chat_id, f"已添加频道：{channel_id}")
                except:
                    send_message(chat_id, "格式错误，请使用 /add 频道ID")
            elif text.startswith("/del "):
                try:
                    channel_id = int(text.split(" ")[1])
                    remove_channel(channel_id)
                    send_message(chat_id, f"已删除频道：{channel_id}")
                except:
                    send_message(chat_id, "格式错误，请使用 /del 频道ID")
            elif text.startswith("/list"):
                channels = get_channels()
                msg_text = "\n".join([f"{v} ({k})" for k, v in channels.items()])
                send_message(chat_id, msg_text or "暂无频道")
            elif text.startswith("/help"):
                help_text = (
                    "/add 频道ID - 添加频道\n"
                    "/del 频道ID - 删除频道\n"
                    "/list - 查看已添加频道\n"
                    "/help - 查看帮助"
                )
                send_message(chat_id, help_text)
            else:
                forward_to_channels(user_id, msg)
        else:
            send_message(chat_id, "你不是管理员，无权限使用该机器人。")

    return {"ok": True}

@app.route("/")
def index():
    return "Bot is running"

if __name__ == "__main__":
    init_db()
    requests.get(f"{API_URL}/setWebhook", params={"url": f"{WEBHOOK_URL}/{TOKEN}"})
    app.run(host="0.0.0.0", port=10000)