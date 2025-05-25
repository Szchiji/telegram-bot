import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from fastapi import FastAPI, Request, Response

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = "-1001763041158"
ADMIN_USER_ID = 7848870377

app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 广播命令
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

# 匿名转发用户消息到频道
async def anonymous_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    bot = context.bot

    if update.effective_chat.type != "private":
        return

    if message.text:
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"📩 匿名消息：\n{message.text}"
            )
            await message.reply_text("✅ 已匿名转发到频道。")
        except Exception as e:
            await message.reply_text(f"❌ 转发失败：{e}")

    elif message.photo:
        photo = message.photo[-1]
        caption = message.caption if message.caption else ""
        try:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo.file_id,
                caption=f"📸 匿名照片：\n{caption}"
            )
            await message.reply_text("✅ 已匿名转发照片到频道。")
        except Exception as e:
            await message.reply_text(f"❌ 转发失败：{e}")
    else:
        await message.reply_text("🤖 暂不支持此类消息匿名转发。")

application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), anonymous_forward))

# FastAPI 路由，Telegram 会调用这个Webhook URL
@app.post("/webhook")
async def webhook(request: Request):
    json_update = await request.json()
    update = Update.de_json(json_update, application.bot)
    await application.update_queue.put(update)
    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    print("启动 Webhook 服务器...")
    # Render 默认使用端口 10000，或者用环境变量 PORT
    import os
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)

