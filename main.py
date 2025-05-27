from flask import Flask, request
import telegram
import json
import os

app = Flask(__name__)

BOT_TOKEN = '7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc'
ADMIN_ID = 5528758975
bot = telegram.Bot(token=BOT_TOKEN)

CHANNEL_FILE = 'channels.json'

if not os.path.exists(CHANNEL_FILE):
    with open(CHANNEL_FILE, 'w') as f:
        json.dump({}, f)

def load_channels():
    with open(CHANNEL_FILE, 'r') as f:
        return json.load(f)

def save_channels(data):
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(data, f)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.channel_post:
        chat = update.channel_post.chat
        channels = load_channels()
        if str(chat.id) not in channels:
            channels[str(chat.id)] = {'title': chat.title, 'enabled': True}
            save_channels(channels)

    elif update.message and update.message.from_user.id == ADMIN_ID:
        text = update.message.text or ""
        args = text.split(maxsplit=1)
        cmd = args[0]

        if cmd == '/broadcast':
            if len(args) < 2:
                bot.send_message(chat_id=ADMIN_ID, text='请输入要广播的消息内容。')
                return 'ok'
            message = args[1]
            channels = load_channels()
            count = 0
            for cid, info in channels.items():
                if info.get('enabled', True):
                    try:
                        bot.send_message(chat_id=int(cid), text=message)
                        count += 1
                    except Exception as e:
                        print(f"发送失败: {cid} - {e}")
            bot.send_message(chat_id=ADMIN_ID, text=f'广播完成，成功发送到 {count} 个频道。')

        elif cmd == '/list_channels':
            channels = load_channels()
            if not channels:
                bot.send_message(chat_id=ADMIN_ID, text='尚未记录任何频道。')
            else:
                lines = []
                for cid, info in channels.items():
                    lines.append(f"{info.get('title', '无名')} ({cid}) - {'✅启用' if info.get('enabled', True) else '❌禁用'}")
                bot.send_message(chat_id=ADMIN_ID, text='\n'.join(lines))

        elif cmd == '/disable_channel':
            if len(args) < 2:
                bot.send_message(chat_id=ADMIN_ID, text='用法：/disable_channel 频道ID')
            else:
                cid = args[1].strip()
                channels = load_channels()
                if cid in channels:
                    channels[cid]['enabled'] = False
                    save_channels(channels)
                    bot.send_message(chat_id=ADMIN_ID, text=f"频道 {cid} 已被禁用。")
                else:
                    bot.send_message(chat_id=ADMIN_ID, text="未找到该频道。")

    return 'ok'

@app.route('/')
def home():
    return 'Bot is running.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
