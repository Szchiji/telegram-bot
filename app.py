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
    payload = {
        "chat_id": int(channel_id),
        "disable_notification": True
    }

    if content_type == "text":
        payload["text"] = content
        url = f"{API_URL}/sendMessage"
    elif content_type == "photo":
        payload["photo"] = content
        url = f"{API_URL}/sendPhoto"
    elif content_type == "video":
        payload["video"] = content
        url = f"{API_URL}/sendVideo"
    else:
        return

    response = requests.post(url, json=payload)
    result = response.json()

    # 自动移除失效频道
    if not result.get("ok"):
        desc = result.get("description", "")
        if "chat not found" in desc or "not enough rights" in desc:
            with open(CHANNELS_FILE, "r") as f:
                channels = json.load(f)
            if str(channel_id) in channels:
                del channels[str(channel_id)]
                with open(CHANNELS_FILE, "w") as f:
                    json.dump(channels, f)

@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    # 记录新加入频道
    if "my_chat_member" in data:
        chat = data["my_chat_member"]["chat"]
        new_status = data["my_chat_member"]["new_chat_member"]["status"]
        if chat["type"] == "channel" and new_status in ["administrator", "member"]:
            save_channel(chat["id"], chat["title"])
        return "ok"

    # 处理消息
    if "message" in data:
        msg = data["message"]
        user_id = msg["from"]["id"]

        if user_id != ADMIN_ID:
            return "not admin"

        if "text" in msg and msg["text"] == "/help":
            help_text = (
                "发送文字、图片或视频后，机器人会弹出频道选择按钮。\n"
                "点击频道按钮即可匿名转发。\n"
                "点击“全部频道”将同时发送到所有频道。\n\n"
                "支持：频道中文名、频道自动记录、多频道群发、/help 指令。"
            )
            requests.post(f"{API_URL}/sendMessage", json={
                "chat_id": ADMIN_ID,
                "text": help_text
            })
            return "ok"

        # 记录内容
        content_type, content_value = None, None
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

        with open("last_message.json", "w") as f:
            json.dump({
                "type": content_type,
                "value": content_value
            }, f)

        # 显示频道按钮
        channels = get_channels()
        buttons = [[{"text": v, "callback_data": k}] for k, v in channels.items()]
        if buttons:
            buttons.append([{"text": "全部频道", "callback_data": "ALL_CHANNELS"}])

        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": ADMIN_ID,
            "text": "请选择要发送到的频道：",
            "reply_markup": {"inline_keyboard": buttons}
        })

    # 处理按钮点击
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
                channels = get_channels()
                for cid in list(channels.keys()):
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
        requests.post(f"{API_URL}/setWebhook", data={"url": WEBHOOK_URL})
    set_webhook()
    app.run(host="0.0.0.0", port=10000)