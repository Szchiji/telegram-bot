from flask import Flask, request
import requests, json, os, uuid

app = Flask(__name__)

# === 配置区（使用环境变量）===
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN')  # e.g. https://telegram-bot-329q.onrender.com
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

CHANNEL_FILE = 'channels.json'
CACHE_FILE = 'message_cache.json'


# ===== 工具函数 =====
def load_channels():
    if not os.path.exists(CHANNEL_FILE):
        return []
    with open(CHANNEL_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_text(chat_id, text):
    requests.post(f'{API_URL}/sendMessage', json={'chat_id': chat_id, 'text': text})

def send_photo(chat_id, file_id, caption=''):
    requests.post(f'{API_URL}/sendPhoto', json={
        'chat_id': chat_id,
        'photo': file_id,
        'caption': caption
    })

def send_video(chat_id, file_id, caption=''):
    requests.post(f'{API_URL}/sendVideo', json={
        'chat_id': chat_id,
        'video': file_id,
        'caption': caption
    })

def show_channel_buttons(chat_id, msg_id):
    channels = load_channels()
    buttons = [
        [{'text': c['name'], 'callback_data': f'{msg_id}|{c["id"]}'}] for c in channels
    ]
    buttons.append([{'text': '全部发送', 'callback_data': f'{msg_id}|ALL'}])

    requests.post(f'{API_URL}/sendMessage', json={
        'chat_id': chat_id,
        'text': '请选择要发送的频道：',
        'reply_markup': {'inline_keyboard': buttons}
    })


# ===== Webhook 主处理 =====
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json()

    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']

        if chat_id == ADMIN_ID and 'text' in message:
            text = message['text']

            if text.startswith('/addchannel'):
                parts = text.split()
                if len(parts) == 2:
                    try:
                        channel_id = int(parts[1])
                    except:
                        send_text(chat_id, '频道ID格式错误，必须是数字。')
                        return '', 200

                    resp = requests.get(f'{API_URL}/getChat', params={'chat_id': channel_id})
                    result = resp.json()
                    if result.get('ok'):
                        chat_info = result['result']
                        name = chat_info.get('title', '未知频道')

                        channels = load_channels()
                        if any(c['id'] == channel_id for c in channels):
                            send_text(chat_id, f'频道 {name} 已存在。')
                            return '', 200

                        channels.append({'id': channel_id, 'name': name})
                        with open(CHANNEL_FILE, 'w', encoding='utf-8') as f:
                            json.dump(channels, f, ensure_ascii=False, indent=2)

                        send_text(chat_id, f'已添加频道：{name} ({channel_id})')
                    else:
                        send_text(chat_id, '获取频道信息失败，请确认机器人已加入频道且ID正确。')
                else:
                    send_text(chat_id, '使用方法：/addchannel <频道ID>')
                return '', 200

        if chat_id != ADMIN_ID:
            return '', 200

        msg_id = str(uuid.uuid4())[:8]
        cache = load_cache()

        if 'text' in message:
            cache[msg_id] = {'type': 'text', 'text': message['text']}
        elif 'photo' in message:
            cache[msg_id] = {
                'type': 'photo',
                'file_id': message['photo'][-1]['file_id'],
                'caption': message.get('caption', '')
            }
        elif 'video' in message:
            cache[msg_id] = {
                'type': 'video',
                'file_id': message['video']['file_id'],
                'caption': message.get('caption', '')
            }
        else:
            send_text(chat_id, '仅支持文本、图片和视频。')
            return '', 200

        save_cache(cache)
        show_channel_buttons(chat_id, msg_id)

    elif 'callback_query' in data:
        cq = data['callback_query']
        chat_id = cq['message']['chat']['id']
        msg_id, channel_id_str = cq['data'].split('|')

        cache = load_cache()
        msg = cache.get(msg_id)
        if not msg:
            requests.post(f'{API_URL}/answerCallbackQuery', json={
                'callback_query_id': cq['id'],
                'text': '消息已失效或未找到。'
            })
            return '', 200

        if channel_id_str == 'ALL':
            channels = load_channels()
            for c in channels:
                target_id = c['id']
                if msg['type'] == 'text':
                    send_text(target_id, msg['text'])
                elif msg['type'] == 'photo':
                    send_photo(target_id, msg['file_id'], msg.get('caption', ''))
                elif msg['type'] == 'video':
                    send_video(target_id, msg['file_id'], msg.get('caption', ''))
        else:
            channel_id = int(channel_id_str)
            if msg['type'] == 'text':
                send_text(channel_id, msg['text'])
            elif msg['type'] == 'photo':
                send_photo(channel_id, msg['file_id'], msg.get('caption', ''))
            elif msg['type'] == 'video':
                send_video(channel_id, msg['file_id'], msg.get('caption', ''))

        del cache[msg_id]
        save_cache(cache)

        requests.post(f'{API_URL}/answerCallbackQuery', json={
            'callback_query_id': cq['id'],
            'text': '发送成功！'
        })

    return '', 200


# ===== 自动设置 Webhook（使用环境变量）=====
@app.before_first_request
def set_webhook():
    if WEBHOOK_DOMAIN:
        url = f"{WEBHOOK_DOMAIN}/{BOT_TOKEN}"
        res = requests.get(f"{API_URL}/setWebhook", params={'url': url})
        print('Webhook 设置结果:', res.json())


@app.route('/')
def index():
    return 'Bot is running.'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)