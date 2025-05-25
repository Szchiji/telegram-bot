import os
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

if not BOT_TOKEN:
    raise ValueError("请设置环境变量 BOT_TOKEN")

banned_users = set()

app = FastAPI()
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 处理广播
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 你不是管理员，无权使用此命令。")
        return
    if not context.args:
        await update.message.reply_text("用法: /broadcast <消息内容>")
        return
    text = " ".join(context.args)
    await context.bot.send_message(CHANNEL_ID, text)
    await update.message.reply_text("✅ 广播已发送。")

# 禁止用户
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 你不是管理员，无权使用此命令。")
        return
    if not context.args:
        await update.message.reply_text("用法: /ban 用户ID或@用户名")
        return

    target = context.args[0]
    target_id = None

    if target.isdigit():
        target_id = int(target)
    else:
        username = target.lstrip("@")
        try:
            user = await context.bot.get_chat(username)
            target_id = user.id
        except Exception:
            await update.message.reply_text(f"找不到用户: {target}")
            return

    banned_users.add(target_id)
    await update.message.reply_text(f"已禁止用户 {target}（ID: {target_id}）。")

# 解除禁止
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 你不是管理员，无权使用此命令。")
        return
    if not context.args:
        await update.message.reply_text("用法: /unban 用户ID或@用户名")
        return

    target = context.args[0]
    target_id = None

    if target.isdigit():
        target_id = int(target)
    else:
        username = target.lstrip("@")
        try:
            user = await context.bot.get_chat(username)
            target_id = user.id
        except Exception:
            await update.message.reply_text(f"找不到用户: {target}")
            return

    if target_id in banned_users:
        banned_users.remove(target_id)
        await update.message.reply_text(f"已解除禁止用户 {target}（ID: {target_id}）。")
    else:
        await update.message.reply_text(f"用户 {target}（ID: {target_id}）未被禁止。")

# 所有非禁言用户消息匿名转发到频道
async def forward_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        # 被禁言，忽略消息
        return
    # 匿名转发消息（仅文本，图片等需自己扩展）
    if update.message.text:
        await context.bot.send_message(CHANNEL_ID, update.message.text)

# 设置路由接收 Telegram Webhook
@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return Response(content="ok")

def main():
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), forward_anonymous))

if __name__ == "__main__":
    main()
