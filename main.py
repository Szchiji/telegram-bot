import os
from flask import Flask, request, abort
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler

TOKEN = "7660420861:AAEZDq7QVIva3aq4jEQpj-xhwdpRp7ceMdc"
WEBHOOK_PATH = "/webhook"  # 你设置的 webhook 路径
WEBHOOK_URL = f"https://telegram-bot-329q.onrender.com{WEBHOOK_PATH}"

app = Flask(__name__)
bot = Bot(token=TOKEN)

# 初始化 Dispatcher，use_context=True 表示用新版上下文机制
dispatcher = Dispatcher(bot, None, workers=0)

def start(update: Update, context):
    update.message.reply_text("机器人启动成功！")

dispatcher.add_handler(CommandHandler("start", start))

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "OK"
    else:
        abort(405)

@app.route("/")
def index():
    return "机器人运行中..."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)