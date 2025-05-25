import os
import json
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 配置区
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377

DATA_FILE = "vip_data.json"

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN:
    raise ValueError("请设置环境变量 BOT_TOKEN")

# 读取或初始化会员数据
def load_data():
    try:import os
import json
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,import os
import json
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 配置区
CHANNEL_ID = -1001763041158  # 你的频道ID
ADMIN_ID = 7848870377        # 你的管理员用户ID

DATA_FILE = "vip_data.json"

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN:
    raise ValueError("请设置环境变量 BOT_TOKEN")

app = FastAPI()

# 会员数据管理
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

vip_data = load_data()  # dict 格式，示例： {"user_id": true, ...}

# 运行 Telegram Bot
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 检查是否是管理员
def is_admin(user_id: int):
    return user_id == ADMIN_ID

# 检查是否是会员
def is_vip(user_id: int):
    return str(user_id) in vip_data and vip_data[str(user_id)] is True

# 命令：添加会员
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("你没有权限执行此命令。")
        return
    if not context.args:
        await update.message.reply_text("用法：/addvip 用户ID")
        return
    target_id = context.args[0]
    vip_data[str(target_id)] = True
    save_data(vip_data)
    await update.message.reply_text(f"成功添加会员 {target_id}")

# 命令：删除会员
async def delvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("你没有权限执行此命令。")
        return
    if not context.args:
        await update.message.reply_text("用法：/delvip 用户ID")
        return
    target_id = context.args[0]
    if str(target_id) in vip_data:
        del vip_data[str(target_id)]
        save_data(vip_data)
        await update.message.reply_text(f"成功删除会员 {target_id}")
    else:
        await update.message.reply_text("该用户不是会员。")

# 审核按钮回调
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # 格式示例： "approve:<user_id>:<message_id>" 或 "reject:<user_id>:<message_id>"
    action, user_id, message_id = data.split(":")
    user_id = int(user_id)
    message_id = int(message_id)

    if not is_admin(query.from_user.id):
        await query.edit_message_text("只有管理员可以操作此按钮。")
        return

    if action == "approve":
        # 从上下文中取消息文本，匿名发送到频道
        # 这里简单直接转发原消息文本
        original_text = context.chat_data.get(message_id)
        if original_text:
            await context.bot.send_message(CHANNEL_ID, text=original_text)
            await query.edit_message_text("已通过并发布到频道。")
        else:
            await query.edit_message_text("原始消息找不到，发布失败。")
    elif action == "reject":
        await query.edit_message_text("已拒绝该消息。")

# 用户消息处理，区分会员和非会员
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    if is_vip(user.id):
        # 会员，直接匿名发到频道
        await context.bot.send_message(CHANNEL_ID, text=text)
        await update.message.reply_text("你是会员，消息已匿名发布到频道。")
    else:
        # 非会员，管理员审核
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("通过", callback_data=f"approve:{user.id}:{update.message.message_id}"),
                InlineKeyboardButton("拒绝", callback_data=f"reject:{user.id}:{update.message.message_id}")
            ]
        ])
        # 保存消息文本供审核时使用
        context.chat_data[update.message.message_id] = text

        await context.bot.send_message(
            ADMIN_ID,
            text=f"用户 @{user.username or user.id} 发送审核消息：\n\n{text}",
            reply_markup=keyboard,
        )
        await update.message.reply_text("你的消息已提交审核，请等待管理员审批。")

# 注册命令和消息处理
application.add_handler(CommandHandler("addvip", addvip))
application.add_handler(CommandHandler("delvip", delvip))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# FastAPI webhook路由
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return Response(status_code=200)

# 启动时设置Webhook（需要在外部调用一次）
async def set_webhook():
    webhook_url = f"https://你的域名{WEBHOOK_PATH}"
    await application.bot.set_webhook(webhook_url)

if __name__ == "__main__":
    import uvicorn
    # 启动时手动调用 set_webhook() 也可以放在启动脚本里调用
    asyncio.run(set_webhook())
    uvicorn.run(app, host="0.0.0.0", port=PORT)

