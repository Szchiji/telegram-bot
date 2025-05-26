from flask import Flask, request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
import json
import os
import requests

TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
WEBHOOK_URL = 'https://telegram-bot-329q.onrender.com/'

app = Flask(__name__)
bot = Bot(token=TOKEN)

CHANNELS_FILE = 'channels.json'
CACHE_FILE = 'cache.json'


def read_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []


def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_channels():
    return read_json(CHANNELS_FILE)


def save_channels(channels):
    write_json(CHANNELS_FILE, channels)


def add_channel(channel_id, title):
    channels = load_channels()
    if not any(c['id'] == channel_id for c in channels):
        channels.append({'id': channel_id, 'title': title})
        save_channels(channels)


def cache_message(msg_type, content):
    write_json(CACHE_FILE, {'type': msg_type, 'content': content})


def get_cached_message():
    return read_json(CACHE_FILE)


def send_channel_keyboard(chat_id):
    channels = load_channels()
    if not channels:
        bot.send_message(chat_id, '机器人还未加入任何频道，请先添加机器人为频道管理员，并在频道发一条消息激活。')
        return

    keyboard = []
    for c in channels:
        keyboard.append([InlineKeyboardButton(c['title'], callback_data=f"toggle_{c['id']}")])
    keyboard.append([InlineKeyboardButton("发送到选中频道", callback_data="send_selected")])

    markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id, '请选择要发送的频道（点击切换选中状态），选完点“发送到选中频道”：', reply_markup=markup)


selected_channels = set()


@app.route('/', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)

    if update.message:
        msg = update.message

        # 频道消息，自动添加频道
        if msg.sender_chat:
            add_channel(msg.sender_chat.id, msg.sender_chat.title or '未知频道')
            return 'ok'

        # 非管理员消息忽略
        if msg.from_user.id != ADMIN_ID:
            return 'ok'

        # 缓存消息内容
        if msg.text:
            cache_message('text', msg.text)
        elif msg.photo:
            file_id = msg.photo[-1].file_id
            cache_message('photo', file_id)
        elif msg.video:
            cache_message('video', msg.video.file_id)
        else:
            return 'ok'

        send_channel_keyboard(ADMIN_ID)
        return 'ok'

    if update.callback_query:
        query = update.callback_query
        data = query.data

        global selected_channels

        if data.startswith('toggle_'):
            channel_id = int(data.split('_')[1])
            if channel_id in selected_channels:
                selected_channels.remove(channel_id)
            else:
                selected_channels.add(channel_id)

            channels = load_channels()
            keyboard = []
            for c in channels:
                prefix = "✅ " if c['id'] in selected_channels else ""
                keyboard.append([InlineKeyboardButton(prefix + c['title'], callback_data=f"toggle_{c['id']}")])
            keyboard.append([InlineKeyboardButton("发送到选中频道", callback_data="send_selected")])
            markup = InlineKeyboardMarkup(keyboard)

            bot.edit_message_reply_markup(chat_id=query.message.chat_id,
                                          message_id=query.message.message_id,
                                          reply_markup=markup)
            query.answer()
            return 'ok'

        if data == 'send_selected':
            msg = get_cached_message()
            if not msg:
                query.answer('没有缓存消息，无法发送')
                return 'ok'

            for ch_id in selected_channels:
                try:
                    if msg['type'] == 'text':
                        bot.send_message(ch_id, msg['content'])
                    elif msg['type'] == 'photo':
                        bot.send_photo(ch_id, msg['content'])
                    elif msg['type'] == 'video':
                        bot.send_video(ch_id, msg['content'])
                except Exception as e:
                    print(f"发送到频道{ch_id}失败: {e}")

            selected_channels.clear()
            query.answer('发送成功！')

            bot.edit_message_reply_markup(chat_id=query.message.chat_id,
                                          message_id=query.message.message_id,
                                          reply_markup=None)
            return 'ok'

    return 'ok'


@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    url = f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}'
    r = requests.get(url)
    return r.text


if __name__ == '__main__':
    app.run(port=5000, debug=True)