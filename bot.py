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
CHANNEL_ID = -1001763041158       # 你的频道ID
ADMIN_ID = 7848870377            # 管理员ID

DATA_FILE = "vip_data.json"

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("请设置环境变量 BOT_TOKEN")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-bot-p5yt.onrender.com{WEBHOOK_PATH}"
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8443"))

# 加载会员数据
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"vips": [], "vip_enabled": True}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 保存会员数据
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load_data()

# 判断是否是会员
def is_vip(user_id):
    return user_id in data.get("vips", [])

# FastAPI app
app = FastAPI()

# Telegram Bot 应用
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 管理员命令: 添加会员
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("无权限执行此命令")
        return
    if not context.args:
        await update.message.reply_text("用法: /addvip 用户ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("请输入有效的用户ID（数字）")
        return
    if user_id not in data["vips"]:
        data["vips"].append(user_id)
        save_data(data)
        await update.message.reply_text(f"已添加用户 {user_id} 为会员")
    else:
        await update.message.reply_text("该用户已经是会员")

# 管理员命令: 删除会员
async def delvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("无权限执行此命令")
        return
    if not context.args:
        await update.message.reply_text("用法: /delvip 用户ID")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("请输入有效的用户ID（数字）")
        return
    if user_id in data["vips"]:
        data["vips"].remove(user_id)
        save_data(data)
        await update.message.reply_text(f"已删除用户 {user_id} 的会员资格")
    else:
        await update.message.reply_text("该用户不是会员")

# 管理员命令: 启用会员免审核
async def enablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("无权限执行此命令")
        return
    data["vip_enabled"] = True
    save_data(data)
    await update.message.reply_text("已启用会员免审核机制")

# 管理员命令: 关闭会员免审核
async def disablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("无权限执行此命令")
        return
    data["vip_enabled"] = False
    save_data(data)
    await update.message.reply_text("已关闭会员免审核机制")

# 管理员命令: 广播消息给所有会员
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("无权限执行此命令")
        return
    if not context.args:
        await update.message.reply_text("用法: /broadcast 内容")
        return
    text = " ".join(context.args)
    count = 0
    for user_id in data.get("vips", []):
        try:
            await application.bot.send_message(chat_id=user_id, text=text)
            count += 1
        except Exception as e:
            print(f"给用户 {user_id} 发送广播失败: {e}")
    await update.message.reply_text(f"已向 {count} 个会员发送广播")

# 普通用户发送消息，管理员审核
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # 如果是会员且免审核开启，直接匿名发频道
    if data.get("vip_enabled", True) and is_vip(user_id):
        await application.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"匿名会员消息：\n{text}"
        )
        await update.message.reply_text("您的消息已匿名发送到频道，无需审核")
        return

    # 普通用户，发送给管理员审核
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("通过", callback_data=f"approve|{user_id}|{text}"),
            InlineKeyboardButton("拒绝", callback_data=f"reject|{user_id}|{text}")
        ]]
    )
    await application.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"用户 {user_id} 发送消息，请审核：\n{text}",
        reply_markup=keyboard
    )
    await update.message.reply_text("您的消息已发送管理员审核，请稍候")

# 回调查询处理审核按钮点击
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_str = query.data
    parts = data_str.split("|")
    if len(parts) < 3:
        await query.edit_message_text("数据错误")
        return

    action, user_id_str, msg_text = parts[0], parts[1], "|".join(parts[2:])
    user_id = int(user_id_str)

    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("无权限操作")
        return

    if action == "approve":
        # 通过，匿名发频道
        await application.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"匿名审核消息：\n{msg_text}"
        )
        await query.edit_message_text(f"已通过用户 {user_id} 的消息")
        try:
            await application.bot.send_message(chat_id=user_id, text="您的消息已通过审核，已发布到频道。")
        except:
            pass
    elif action == "reject":
        await query.edit_message_text(f"已拒绝用户 {user_id} 的消息")
        try:
            await application.bot.send_message(chat_id=user_id, text="您的消息未通过审核。")
        except:
            pass

# 注册处理器
application.add_handler(CommandHandler("addvip", addvip))
application.add_handler(CommandHandler("delvip", delvip))
application.add_handler(CommandHandler("enablevip", enablevip))
application.add_handler(CommandHandler("disablevip", disablevip))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), user_message))
application.add_handler(CallbackQueryHandler(button_handler))

# FastAPI webhook 接收
@app.post(WEBHOOK_PATH)
async def webhook(req: Request):
    body = await req.json()
    update = Update.de_json(body, application.bot)
    await application.update_queue.put(update)
    return Response(status_code=200)

# 启动时设置 webhook
async def on_startup():
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook 已设置: {WEBHOOK_URL}")

if __name__ == "__main__":
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    uvicorn.run(app, host=HOST, port=PORT)

