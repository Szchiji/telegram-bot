import os
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")  # 从环境变量中读取
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1001763041158")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7848870377"))

# 创建 FastAPI 应用
app = FastAPI()

# 创建 Telegram Application
application = Application.builder().token(BOT_TOKEN).build()

# 日志配置
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# 命令：/broadcast
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ 你没有权限使用此命令。")
        return

    if not context.args:
        await update.message.reply_text("⚠️ 请在命令后输入要广播的内容。")
        return

    text = " ".join(context.args)
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await update.message.reply_text("✅ 广播成功。")
    except Exception as e:
        await update.message.reply_text(f"❌ 发送失败：{e}")

# 匿名转发普通用户消息
async def anonymous_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    message = update.message
    if message.text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📩 匿名消息：\n{message.text}")
        await message.reply_text("✅ 已匿名转发到频道。")
    elif message.photo:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id,
                                     caption=f"📷 匿名图片：\n{message.caption or ''}")
        await message.reply_text("✅ 已匿名转发图片到频道。")
    else:
        await message.reply_text("❌ 不支持的消息类型。")

# 添加处理器
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), anonymous_forward))

# FastAPI 路由，Telegram 调用 Webhook 发送消息时触发
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return Response(status_code=200)

# 本地开发调试
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
