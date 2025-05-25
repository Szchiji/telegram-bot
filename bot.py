import json
import os
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377
WEBHOOK_PATH = "/webhook"

BANNED_FILE = "banned_users.json"

app = FastAPI()
bot = Bot(BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# 读取禁止名单
def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

# 保存禁止名单
def save_banned(banned_set):
    with open(BANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(banned_set), f, ensure_ascii=False, indent=2)

banned_users = load_banned()

def is_banned(user):
    if not user:
        return False
    uid_str = str(user.id)
    uname = (user.username or "").lower()
    fname = (user.first_name or "").lower()
    lname = (user.last_name or "").lower()
    # 用户id/用户名/名字/姓氏任意匹配
    return (uid_str in banned_users or
            uname in banned_users or
            fname in banned_users or
            lname in banned_users)

async def handle_message(update: Update, context):
    user = update.effective_user
    if is_banned(user):
        return  # 被禁止，忽略消息
    
    message = update.effective_message
    text = message.text or message.caption or ""
    if not text:
        text = "[非文本消息]"

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML"
    )

async def broadcast(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.effective_message.reply_text("你不是管理员，无权广播。")
        return
    args = context.args
    if not args:
        await update.effective_message.reply_text("请提供广播内容。用法：/broadcast 内容")
        return
    text = " ".join(args)
    await bot.send_message(chat_id=CHANNEL_ID, text=f"【管理员广播】\n\n{text}")
    await update.effective_message.reply_text("广播已发送。")

async def ban(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.effective_message.reply_text("你不是管理员，无权禁言。")
        return
    args = context.args
    if not args:
        await update.effective_message.reply_text("请提供要禁止的用户id或用户名或昵称。用法：/ban 用户")
        return
    user_identifier = args[0].lower()
    banned_users.add(user_identifier)
    save_banned(banned_users)
    await update.effective_message.reply_text(f"已禁止用户：{user_identifier}")

async def unban(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.effective_message.reply_text("你不是管理员，无权解禁。")
        return
    args = context.args
    if not args:
        await update.effective_message.reply_text("请提供要解除禁止的用户id或用户名或昵称。用法：/unban 用户")
        return
    user_identifier = args[0].lower()
    if user_identifier in banned_users:
        banned_users.remove(user_identifier)
        save_banned(banned_users)
        await update.effective_message.reply_text(f"已解除禁止用户：{user_identifier}")
    else:
        await update.effective_message.reply_text(f"用户 {user_identifier} 不在禁止列表。")

async def telegram_update(update: Update, context):
    if update.message:
        user = update.effective_user
        if is_banned(user):
            return
        # 非命令消息处理转发
        if not update.message.text or not update.message.text.startswith("/"):
            await handle_message(update, context)

# 注册命令
dispatcher.add_handler(CommandHandler("broadcast", broadcast))
dispatcher.add_handler(CommandHandler("ban", ban))
dispatcher.add_handler(CommandHandler("unban", unban))
dispatcher.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), telegram_update))

@app.post(WEBHOOK_PATH)
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await dispatcher.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Bot is running."}
