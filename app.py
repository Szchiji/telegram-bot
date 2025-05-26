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

def save_channel(channel_id, title):
    with open(CHANNELS_FILE, "r") as f:
        data = json.load(f)
    if str(channel_id) not in data:
        data[str(channel_id)] = title
        with open(CHANNELS_FILE, "w") as f:
            json.dump(data, f)

def get_channels():
    with open(CHANNELS_FILE, "r") as f:
        return json.load(f)

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
            text = msg["text"]

            if text == "/help":
                help_text = (
                    "发送文字、图片或视频后，机器人会弹出频道选择按钮。\n"
                    "点击频道按钮，即可匿名转发到该频道。\n"
                    "也可以点击“全部频道”转发给所有频道。\n\n"
                    "当前支持：\n"
                    "- 中文频道按钮\n"
                    "- 自动记录频道\n"
                    "- 一键多频道群发\n"
                    "- /help 命令"
                )
                requests.post(f"{API_URL}/sendMessage", json={
                    "chat_id": ADMIN_ID,
                    "text": help_text
                })
                return "ok"

            content_type = "text"
            content_value = text

        elif "photo" in msg:
            content_type = "photo"
            content_value = msg["photo"][-1]["file_id"]
        elif "video" in msg:
            content_type = "video"
            content_value = msg["video"]["file_id"]
        else:
            return "unsupported"

        with open("last_message.json", "w") as f:
            json.dump({
                "type": content_type,
                "value": content_value
            }, f)

        channels = get_channels()
        buttons = [[{"text": v, "callback_data": k}] for k, v in channels.items()]
        buttons.append([{"text": "全部频道", "callback_data": "ALL_CHANNELS"}])

        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": ADMIN_ID,
            "text": "请选择要发送到的频道：",
            "reply_markup": {"inline_keyboard": buttons}
        })

    elif "callback_query" in data:
        query = data["callback_query"]
        user_id = query["from"]["id"]
        data_value = query["data"]

        if user_id != ADMIN_ID:
            return "not admin"

        if os.path.exists("last_message.json"):
            with open("last_message.json", "r") as f:
                msg_data = json.load(f)

            if data_value == "ALL_CHANNELS":
                for cid in get_channels().keys():
                    send_to_channel(cid, msg_data["value"], msg_data["type"])
                answer = "已发送到全部频道！"
            else:
                send_to_channel(data_value, msg_data["value"], msg_data["type"])
                answer = "已发送！"

            requests.post(f"{API_URL}/answerCallbackQuery", json={
                "callback_query_id": query["id"],
                "text": answer,
                "show_alert": False
            })

    return "ok"

if __name__ == "__main__":
    def set_webhook():
        url = f"{API_URL}/setWebhook"
        requests.post(url, data={"url": WEBHOOK_URL})
    set_webhook()
    app.run(host="0.0.0.0", port=10000)