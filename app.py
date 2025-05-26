from flask import Flask, request
import requests
import json
import os

TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
ADMIN_ID = 5528758975
API_URL = f"https://api.telegram.org/bot{TOKEN}"
WEBHOOK_URL = "https://telegram-bot-329q.onrender.com"

app = Flask(__name__)

CHANNELS_FILE = "channels.json"
if not os.path.exists(CHANNELS_FILE):
    with open(CHANNELS_FILE, "w") as f:
        json.dump({}, f)

# 保存频道
def save_channel(channel_id, title):
    with open(CHANNELS_FILE, "r") as f:
        data = json.load(f)
    if str(channel_id) not in data:
        data[str(channel_id)] = title
        with open(CHANNELS_FILE, "w") as f:
            json.dump(data, f)

# 获取所有频道
def get_channels():
    with open(CHANNELS_FILE, "r") as f:
        return json.load(f)

# 设置 Webhook（首次部署时使用）
def set_webhook():
    url = f"{API_URL}/setWebhook"
    response = requests.post(url, data={"url": WEBHOOK_URL})
    return response.json()

# 发送消息到频道
def send_to_channel(channel_id, content, content_type):
    if content_type == "text":
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": channel_id,
            "text": content,
            "disable_notification": True
        })
    elif content_type == "photo":
        requests.post(f"{API_URL}/sendPhoto", json={
            "chat_id": channel_id,
            "photo": content,
            "caption": "",
            "disable_notification": True
        })
    elif content_type == "video":
        requests.post(f"{API_URL}/sendVideo", json={
            "chat_id": channel_id,
            "video": content,
            "caption": "",
            "disable_notification": True
        })

@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    if "my_chat_member" in data:
        chat = data["my_chat_member"]["chat"]
        new_status = data["my_chat_member"]["new_chat_member"]["status"]
        if chat["type"] == "channel" and new_status in ["administrator", "member"]:
            save_channel(chat["id"], chat["title"])
        return "ok"

    if "message" in data:
        msg = data["message"]
        user_id = msg["from"]["id"]

        if user_id != ADMIN_ID:
            return "not admin"

        msg_id = msg["message_id"]
        content_type = None
        content_value = None

        if "text" in msg:
            content_type = "text"
            content_value = msg["text"]
        elif "photo" in msg:
            content_type = "photo"
            content_value = msg["photo"][-1]["file_id"]
        elif "video" in msg:
            content_type = "video"
            content_value = msg["video"]["file_id"]
        else:
            return "unsupported"

        # 存入缓存
        with open("last_message.json", "w") as f:
            json.dump({
                "type": content_type,
                "value": content_value
            }, f)

        # 弹出频道按钮
        channels = get_channels()
        buttons = [[{"text": v, "callback_data": k}] for k, v in channels.items()]
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": ADMIN_ID,
            "text": "请选择要发送到的频道：",
            "reply_markup": {"inline_keyboard": buttons}
        })

    elif "callback_query" in data:
        query = data["callback_query"]
        channel_id = query["data"]
        user_id = query["from"]["id"]

        if user_id != ADMIN_ID:
            return "not admin"

        # 读取缓存消息
        if os.path.exists("last_message.json"):
            with open("last_message.json", "r") as f:
                msg_data = json.load(f)
            send_to_channel(channel_id, msg_data["value"], msg_data["type"])
            requests.post(f"{API_URL}/answerCallbackQuery", json={
                "callback_query_id": query["id"],
                "text": "发送成功！"
            })

    return "ok"

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)