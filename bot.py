import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 配置日志，方便调试
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量读取配置
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("请确保环境变量 BOT_TOKEN 和 WEBHOOK_URL 已正确设置")

# /start 命令处理函数
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("你好！机器人已启动，欢迎使用。")

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 添加命令处理器
    app.add_handler(CommandHandler("start", start))

    # 启动 webhook 服务器
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,  # webhook 路径设置为 token，安全
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
