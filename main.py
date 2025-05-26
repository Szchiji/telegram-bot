from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
API_URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 5528758975

CHANNELS_FILE = 'channels.json'
CACHE_FILE = 'cache.json'


# === 文件读写工具函数 ===

def read_json(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# === 频道管理 ===

def load_channels():
    return read_json(CHANNELS_FILE)

def save_channels(channels):
    write_json(CHANNELS_FILE, channels)

def add_channel(channel_id, channel_title):
    channels = load_channels()
    if not any(c['id'] == channel_id for c in channels):
        channels.append({'id': channel_id, 'title': channel_title})
        save_channels(channels)
        print(f"新频道已添加: {channel_title} ({channel_id})")
    else:
        print(f"频道已存在: {channel_title} ({channel_id})")


# === 消息缓存管理 ===

def cache_message(msg_type, content):
    write_json(CACHE_FILE, {'type': msg_type, 'content': content})

def get_cached_message():
    data = read_json(CACHE_FILE)
    return data if data else None


# === Telegram API 请求 ===

def telegram_api_post(method, data):
    url = API_URL + method
    resp = requests.post(url, json=data)
    if not resp.ok:
        print(f"Telegram API 请求失败 {method}，状态码：{resp.status_code}，内容：{resp.text}")
    return resp.json()


# === 发送频道选择按钮 ===

def send_channel_keyboard(chat_id):
    channels = load_channels()
    if not channels:
        telegram_api_post('sendMessage', {
            'chat_id': chat_id,
            'text': '机器人还未加入任何频道，请先把机器人添加为频道管理员，并在频道发送一条消息激活。'
        })
        return

    keyboard = [[{'text': c['title'], 'callback_data': str(c['id'])}] for c in channels]

    telegram_api_post('sendMessage', {
        'chat_id': chat_id,
        'text': '请选择发送的频道：',
        'reply_markup': {'inline_keyboard': keyboard}
    })


# === 转发消息到频道 ===

def forward_message_to_channel(channel_id, message):
    if not message:
        print("无缓存消息可发送")
        return

    msg_type = message.get('type')
    content = message.get('content')

    if msg_type == 'text':
        telegram_api_post('sendMessage', {
            'chat_id': channel_id,
            'text': content
        })
    elif msg_type == 'photo':
        telegram_api_post('sendPhoto', {
            'chat_id': channel_id,
            'photo': content
        })
    elif msg_type == 'video':
        telegram_api_post('sendVideo', {
            'chat_id': channel_id,
            'video': content
        })


# === 处理消息逻辑 ===

@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()

    # 1. 自动识别频道消息，自动添加频道
    if 'message' in update:
        msg = update['message']

        # 如果消息来自频道（机器人为管理员时）
        if 'sender_chat' in msg:
            sender_chat = msg['sender_chat']
            add_channel(sender_chat['id'], sender_chat.get('title', '未知频道'))
            return 'ok'

        # 普通用户消息，判断是否管理员发来
        if 'from' in msg:
            user_id = msg['from']['id']
            if user_id != ADMIN_ID:
                return 'ok'

            # 缓存消息类型和内容
            if 'text' in msg:
                cache_message('text', msg['text'])
            elif 'photo' in msg:
                # 取最高质量图片file_id
                file_id = msg['photo'][-1]['file_id']
                cache_message('photo', file_id)
            elif 'video' in msg:
                cache_message('video', msg['video']['file_id'])
            else:
                # 不支持的消息类型忽略
                return 'ok'

            # 回复频道选择按钮
            send_channel_keyboard(user_id)
            return 'ok'

    # 2. 处理频道选择按钮点击回调
    if 'callback_query' in update:
        callback = update['callback_query']
        channel_id = callback['data']
        msg = get_cached_message()

        forward_message_to_channel(channel_id, msg)

        # 回调答复
        telegram_api_post('answerCallbackQuery', {
            'callback_query_id': callback['id'],
            'text': '发送成功！'
        })

        return 'ok'

    return 'ok'


if __name__ == '__main__':
    app.run(debug=True, port=5000)