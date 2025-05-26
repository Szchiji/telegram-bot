from flask import Flask, request
import requests, json, os, uuid

app = Flask(__name__)

# 你的机器人 Token 和管理员 ID
BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

# 文件路径
CHANNEL_FILE = 'channels.json'
CACHE_FILE = 'message_cache.json'

# 加载频道列表
def load_channels():
    with open(CHANNEL_FILE, 'r') as f:
        return json.load(f)

# 加载/保存消息缓存
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, 'r') as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

# 发送消息函数
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

# 主 webhook 路由
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json()

    # 普通消息
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']

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

    # 按钮回调
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

# 显示频道按钮
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

@app.route('/')
def index():
    return 'Bot is running.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)