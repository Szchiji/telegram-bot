from flask import Flask, request
import requests, json, os, uuid, threading

app = Flask(__name__)

# === 配置区（环境变量）===
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN')  # e.g. https://yourdomain.com
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

CHANNEL_FILE = 'channels.json'
CACHE_FILE = 'message_cache.json'

file_lock = threading.Lock()


# ===== 文件读写封装 =====
def load_json(filename, default):
    with file_lock:
        if not os.path.exists(filename):
            return default
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'加载 {filename} 失败: {e}')
            return default


def save_json(filename, data):
    with file_lock:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'保存 {filename} 失败: {e}')


# ===== Telegram API 请求封装 =====
def send_request(method, data):
    try:
        resp = requests.post(f'{API_URL}/{method}', json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'请求 Telegram API {method} 失败: {e}')
        return None


def send_text_message(chat_id, text):
    return send_request('sendMessage', {'chat_id': chat_id, 'text': text})


def send_photo_message(chat_id, file_id, caption=''):
    return send_request('sendPhoto', {'chat_id': chat_id, 'photo': file_id, 'caption': caption})


def send_video_message(chat_id, file_id, caption=''):
    return send_request('sendVideo', {'chat_id': chat_id, 'video': file_id, 'caption': caption})


def edit_message_reply_markup(chat_id, message_id, reply_markup):
    return send_request('editMessageReplyMarkup', {
        'chat_id': chat_id,
        'message_id': message_id,
        'reply_markup': reply_markup
    })


def answer_callback_query(callback_query_id, text):
    return send_request('answerCallbackQuery', {
        'callback_query_id': callback_query_id,
        'text': text,
        'show_alert': False
    })


# ===== 频道管理 =====
def load_channels():
    return load_json(CHANNEL_FILE, [])


def save_channels(channels):
    save_json(CHANNEL_FILE, channels)


def add_channel(channel_id):
    channels = load_channels()
    if any(c['id'] == channel_id for c in channels):
        return False, '频道已存在'
    try:
        resp = requests.get(f'{API_URL}/getChat', params={'chat_id': channel_id}, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f'获取频道信息异常: {e}')
        return False, '获取频道信息异常'

    if not data.get('ok'):
        return False, '获取频道信息失败，请确认机器人已加入频道且ID正确'

    title = data['result'].get('title', '未知频道')
    channels.append({'id': channel_id, 'name': title})
    save_channels(channels)
    return True, title


def del_channel(channel_id):
    channels = load_channels()
    new_channels = [c for c in channels if c['id'] != channel_id]
    if len(new_channels) == len(channels):
        return False
    save_channels(new_channels)
    return True


def list_channels_text():
    channels = load_channels()
    if not channels:
        return "频道列表为空。"
    lines = [f"{c['name']}（{c['id']}）" for c in channels]
    return "当前频道列表：\n" + "\n".join(lines)


# ===== 缓存消息 =====
def load_cache():
    return load_json(CACHE_FILE, {})


def save_cache(data):
    save_json(CACHE_FILE, data)


# ===== 频道选择按钮 =====
def build_channel_buttons(msg_id):
    channels = load_channels()
    buttons = [[{'text': c['name'], 'callback_data': f'{msg_id}|{c["id"]}'}] for c in channels]
    buttons.append([{'text': '全部发送', 'callback_data': f'{msg_id}|ALL'}])
    return {'inline_keyboard': buttons}


def prompt_channel_selection(chat_id, message_id, msg_id):
    reply_markup = build_channel_buttons(msg_id)
    edit_message_reply_markup(chat_id, message_id, reply_markup)


# ===== Webhook 主处理 =====
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json()

    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']

        # 管理员命令处理
        if chat_id == ADMIN_ID and 'text' in message:
            text = message['text'].strip()
            if text.startswith('/addchannel'):
                parts = text.split()
                if len(parts) == 2:
                    try:
                        channel_id = int(parts[1])
                    except ValueError:
                        send_text_message(chat_id, '频道ID格式错误，必须是数字。')
                        return '', 200

                    success, msg = add_channel(channel_id)
                    if success:
                        send_text_message(chat_id, f'已添加频道：{msg} ({channel_id})')
                    else:
                        send_text_message(chat_id, msg)
                else:
                    send_text_message(chat_id, '使用方法：/addchannel <频道ID>')
                return '', 200

            elif text.startswith('/delchannel'):
                parts = text.split()
                if len(parts) == 2:
                    try:
                        channel_id = int(parts[1])
                    except ValueError:
                        send_text_message(chat_id, '频道ID格式错误，必须是数字。')
                        return '', 200

                    if del_channel(channel_id):
                        send_text_message(chat_id, f'已删除频道：{channel_id}')
                    else:
                        send_text_message(chat_id, '频道ID不存在。')
                else:
                    send_text_message(chat_id, '使用方法：/delchannel <频道ID>')
                return '', 200

            elif text == '/listchannels':
                send_text_message(chat_id, list_channels_text())
                return '', 200

        # 仅管理员允许发送内容缓存后选择频道
        if chat_id != ADMIN_ID:
            return '', 200

        msg_id = str(uuid.uuid4())[:8]
        cache = load_cache()

        # 只支持文本、单张图片、单个视频
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
            send_text_message(chat_id, '仅支持文本、图片和视频。')
            return '', 200

        save_cache(cache)

        # 显示频道选择按钮，用编辑消息方式
        prompt_channel_selection(chat_id, message['message_id'], msg_id)

    elif 'callback_query' in data:
        cq = data['callback_query']
        chat_id = cq['message']['chat']['id']
        message_id = cq['message']['message_id']
        callback_id = cq['id']

        # 解析回调数据
        try:
            msg_id, channel_id_str = cq['data'].split('|')
        except Exception:
            answer_callback_query(callback_id, '回调数据格式错误。')
            return '', 200

        cache = load_cache()
        msg = cache.get(msg_id)
        if not msg:
            answer_callback_query(callback_id, '消息已失效或未找到。')
            return '', 200

        # 发送内容到目标频道
        if channel_id_str == 'ALL':
            channels = load_channels()
            if not channels:
                answer_callback_query(callback_id, '频道列表为空。')
                return '', 200

            for c in channels:
                target_id = c['id']
                if msg['type'] == 'text':
                    send_text_message(target_id, msg['text'])
                elif msg['type'] == 'photo':
                    send_photo_message(target_id, msg['file_id'], msg.get('caption', ''))
                elif msg['type'] == 'video':
                    send_video_message(target_id, msg['file_id'], msg.get('caption', ''))

            answer_callback_query(callback_id, '已发送到全部频道。')
        else:
            try:
                channel_id = int(channel_id_str)
            except ValueError:
                answer_callback_query(callback_id, '频道ID格式错误。')
                return '', 200

            if msg['type'] == 'text':
                send_text_message(channel_id, msg['text'])
            elif msg['type'] == 'photo':
                send_photo_message(channel_id, msg['file_id'], msg.get('caption', ''))
            elif msg['type'] == 'video':
                send_video_message(channel_id, msg['file_id'], msg.get('caption', ''))

            answer_callback_query(callback_id, '发送成功！')

        # 删除缓存消息
        del cache[msg_id]
        save_cache(cache)

        # 移除按钮（编辑为空按钮）
        edit_message_reply_markup(chat_id, message_id, {'inline_keyboard': []})

    return '', 200


# ===== 自动设置 Webhook =====
@app.before_first_request
def set_webhook():
    if WEBHOOK_DOMAIN:
        url = f"{WEBHOOK_DOMAIN}/{BOT_TOKEN}"
        try:
            res = requests.get(f"{API_URL}/setWebhook", params={'url': url}, timeout=10)
            print('Webhook 设置结果:', res.json())
        except Exception as e:
            print('设置 Webhook 失败:', e)


@app.route('/')
def index():
    return 'Bot is running.'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)