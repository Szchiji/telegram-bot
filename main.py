from flask import Flask, request
import requests, json, os, uuid, threading

app = Flask(__name__)

# === 目录 & 环境变量配置 ===
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
BOT_TOKEN      = os.getenv('BOT_TOKEN')
ADMIN_ID       = int(os.getenv('ADMIN_ID'))
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN')  # e.g. https://telegram-bot-329q.onrender.com
API_URL        = f'https://api.telegram.org/bot{BOT_TOKEN}'

CHANNEL_FILE   = os.path.join(BASE_DIR, 'channels.json')
CACHE_FILE     = os.path.join(BASE_DIR, 'message_cache.json')
file_lock      = threading.Lock()


# === JSON 读写（线程安全） ===
def load_json(fn, default):
    with file_lock:
        if os.path.exists(fn):
            try:
                with open(fn, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f'加载 {fn} 失败: {e}')
        return default

def save_json(fn, data):
    with file_lock:
        try:
            with open(fn, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'保存 {fn} 失败: {e}')


# === 频道列表管理 ===
def load_channels():
    return load_json(CHANNEL_FILE, [])

def save_channels(channels):
    save_json(CHANNEL_FILE, channels)

def del_channel(cid):
    ch = load_channels()
    new = [c for c in ch if c['id'] != cid]
    if len(new) == len(ch):
        return False
    save_channels(new)
    return True

def list_channels_text():
    ch = load_channels()
    if not ch:
        return "频道列表为空。"
    return "\n".join(f"{c['name']}（{c['id']}）" for c in ch)


# === 消息缓存管理 ===
def load_cache():
    return load_json(CACHE_FILE, {})

def save_cache(cache):
    save_json(CACHE_FILE, cache)


# === Telegram API 简易封装 ===
def api(method, data):
    try:
        r = requests.post(f"{API_URL}/{method}", json=data, timeout=10)
        return r.json()
    except Exception as e:
        print(f"调用 API {method} 失败: {e}")
        return None

def send_message(cid, text):
    api('sendMessage', {'chat_id': cid, 'text': text})

def send_media(cid, msg):
    if msg['type'] == 'text':
        send_message(cid, msg['text'])
    elif msg['type'] == 'photo':
        api('sendPhoto', {'chat_id': cid, 'photo': msg['file_id'], 'caption': msg.get('caption','')})
    elif msg['type'] == 'video':
        api('sendVideo', {'chat_id': cid, 'video': msg['file_id'], 'caption': msg.get('caption','')})

def edit_buttons(cid, mid, markup):
    api('editMessageReplyMarkup', {'chat_id': cid, 'message_id': mid, 'reply_markup': markup})

def answer_cb(cbid, text):
    api('answerCallbackQuery', {'callback_query_id': cbid, 'text': text, 'show_alert': False})


# === 构建频道选择按钮 ===
def build_buttons(msg_id):
    ch = load_channels()
    btns = [[{'text': c['name'], 'callback_data': f'{msg_id}|{c["id"]}'}] for c in ch]
    btns.append([{'text': '全部发送', 'callback_data': f'{msg_id}|ALL'}])
    return {'inline_keyboard': btns}


# === Webhook 主处理 ===
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json() or {}
    # —— 打印全部更新到日志 —— 
    print("🔔 收到更新:", json.dumps(data, ensure_ascii=False))

    # —— 自动添加频道 —— 
    if 'my_chat_member' in data:
        mc = data['my_chat_member']
        chat = mc['chat']
        status = mc['new_chat_member']['status']
        if status in ('administrator', 'creator') and chat.get('title'):
            cid, name = chat['id'], chat['title']
            channels = load_channels()
            if not any(c['id']==cid for c in channels):
                channels.append({'id':cid,'name':name})
                save_channels(channels)
                print(f"自动添加频道：{name}（{cid}）")
        return '', 200

    # —— 普通消息 & 命令 —— 
    if 'message' in data:
        msg = data['message']
        cid = msg['chat']['id']

        # 管理员命令
        if cid == ADMIN_ID and 'text' in msg:
            t = msg['text'].strip()
            if t.startswith('/delchannel'):
                parts = t.split()
                if len(parts)==2 and parts[1].lstrip('-').isdigit():
                    ok = del_channel(int(parts[1]))
                    send_message(cid, '删除成功' if ok else '频道ID不存在')
                else:
                    send_message(cid, '用法：/delchannel <频道ID>')
                return '', 200
            if t == '/listchannels':
                send_message(cid, list_channels_text())
                return '', 200

        # 非管理员不处理后续
        if cid != ADMIN_ID:
            return '', 200

        # 缓存并弹按钮
        key = str(uuid.uuid4())[:8]
        cache = load_cache()
        if 'text' in msg:
            cache[key] = {'type':'text','text':msg['text']}
        elif 'photo' in msg:
            cache[key] = {'type':'photo','file_id':msg['photo'][-1]['file_id'],'caption':msg.get('caption','')}
        elif 'video' in msg:
            cache[key] = {'type':'video','file_id':msg['video']['file_id'],'caption':msg.get('caption','')}
        else:
            send_message(cid, '仅支持文本、图片、视频')
            return '', 200

        save_cache(cache)
        edit_buttons(cid, msg['message_id'], build_buttons(key))
        return '', 200

    # —— 按钮回调 —— 
    if 'callback_query' in data:
        cq = data['callback_query']
        cbid = cq['id']
        cid = cq['message']['chat']['id']
        mid = cq['message']['message_id']
        try:
            key, dest = cq['data'].split('|')
        except:
            answer_cb(cbid,'无效操作')
            return '', 200

        cache = load_cache()
        m = cache.get(key)
        if not m:
            answer_cb(cbid,'消息已失效')
            return '', 200

        if dest=='ALL':
            for c in load_channels():
                send_media(c['id'], m)
            answer_cb(cbid,'已发送到全部频道')
        else:
            try:
                send_media(int(dest), m)
                answer_cb(cbid,'发送成功')
            except:
                answer_cb(cbid,'发送失败')

        cache.pop(key,None)
        save_cache(cache)
        edit_buttons(cid, mid, {'inline_keyboard':[]})
        return '', 200

    return '', 200


# === 首次请求前设置 Webhook 并订阅更新类型 ===
@app.before_request
def ensure_webhook():
    if not getattr(app, '_hooked', False) and WEBHOOK_DOMAIN:
        url = f"{WEBHOOK_DOMAIN}/{BOT_TOKEN}"
        res = requests.post(
            f"{API_URL}/setWebhook",
            data={
                'url': url,
                'allowed_updates': json.dumps(['message','callback_query','my_chat_member'])
            },
            timeout=10
        )
        print('Webhook 设置结果:', res.json())
        app._hooked = True


@app.route('/')
def index():
    return 'Bot is running.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)