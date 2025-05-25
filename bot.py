import json
import os
from fastapi import FastAPI, Request
import uvicorn
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = "-1001763041158"
ADMIN_ID = 7848870377
WEBHOOK_URL = "https://telegram-bot-p5yt.onrender.com"
VIP_FILE = "vip_users.json"

enable_vip_mode = True

def load_vip_users():
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, 'r') as f:
            return json.load(f)
    return []

def save_vip_users(users):
    with open(VIP_FILE, 'w') as f:
        json.dump(users, f)

vip_users = load_vip_users()

app = FastAPI()
bot = telegram.Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return "ok"

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("欢迎使用匿名投稿机器人！发送消息开始投稿。")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text("发送你想要匿名投稿的内容，我们会审核后发布到频道。")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    message = update.message
    if enable_vip_mode and user_id in vip_users:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"匿名投稿：\n{message.text}")
        await message.reply_text("✅ 投稿成功，已直接发布。")
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ 通过", callback_data=f"approve|{user_id}|{message.message_id}"),
                InlineKeyboardButton("❌ 拒绝", callback_data=f"reject|{user_id}|{message.message_id}")
            ]
        ])
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"用户 {user_id} 的投稿请求：\n{message.text}", reply_markup=keyboard)
        await message.reply_text("⏳ 投稿已提交，等待管理员审核。")

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action, target_user_id, message_id = data[0], int(data[1]), int(data[2])

    if action == "approve":
        original_message = await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=target_user_id, message_id=message_id)
        if original_message.text:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"匿名投稿：\n{original_message.text}")
        elif original_message.caption:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=original_message.photo[-1].file_id, caption=f"匿名投稿：\n{original_message.caption}")
        await query.message.edit_text(f"✅ 已通过\n\n原文由用户 {target_user_id} 提交")
        await context.bot.send_message(chat_id=target_user_id, text="✅ 你的投稿已被通过并发布。")

    elif action == "reject":
        await query.message.edit_text(f"❌ 已拒绝\n\n原文由用户 {target_user_id} 提交")
        await context.bot.send_message(chat_id=target_user_id, text="❌ 很抱歉，你的投稿未被通过。")

async def add_vip(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target = context.args[0]
        if target.startswith("@"):  # 用户名
            user = await context.bot.get_chat(target)
            user_id = user.id
        else:
            user_id = int(target)
        if user_id not in vip_users:
            vip_users.append(user_id)
            save_vip_users(vip_users)
            await update.message.reply_text(f"✅ 已添加 {user_id} 为会员。")
        else:
            await update.message.reply_text(f"⚠️ 用户 {user_id} 已是会员。")
    except Exception as e:
        await update.message.reply_text("❌ 添加会员失败。请确保输入格式正确。")

async def del_vip(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target = context.args[0]
        if target.startswith("@"):  # 用户名
            user = await context.bot.get_chat(target)
            user_id = user.id
        else:
            user_id = int(target)
        if user_id in vip_users:
            vip_users.remove(user_id)
            save_vip_users(vip_users)
            await update.message.reply_text(f"✅ 已移除 {user_id} 的会员资格。")
        else:
            await update.message.reply_text(f"⚠️ 用户 {user_id} 不是会员。")
    except Exception as e:
        await update.message.reply_text("❌ 删除会员失败。请确保输入格式正确。")

async def enable_vip(update: Update, context: CallbackContext):
    global enable_vip_mode
    if update.effective_user.id == ADMIN_ID:
        enable_vip_mode = True
        await update.message.reply_text("✅ 已启用会员免审核功能。")

async def disable_vip(update: Update, context: CallbackContext):
    global enable_vip_mode
    if update.effective_user.id == ADMIN_ID:
        enable_vip_mode = False
        await update.message.reply_text("✅ 已关闭会员免审核功能。")

async def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    message = " ".join(context.args)
    for user_id in vip_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except:
            pass

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("addvip", add_vip))
application.add_handler(CommandHandler("delvip", del_vip))
application.add_handler(CommandHandler("enablevip", enable_vip))
application.add_handler(CommandHandler("disablevip", disable_vip))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(button_handler))

if __name__ == '__main__':
    import asyncio
    async def main():
        await bot.set_webhook(WEBHOOK_URL)
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
    asyncio.run(main())
