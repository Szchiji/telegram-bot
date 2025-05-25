import json
import os
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377
WEBHOOK_PATH = "/webhook"

BANNED_FILE = "banned_users.json"

app = FastAPI()

# 读写禁止列表
def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

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
    return (uid_str in banned_users or
            uname in banned_users or
            fname in banned_users or
            lname in banned_users)

# 下面的处理函数均使用 async def，参数要加 (update: Update, context: ContextTypes.DEFAULT_TYPE)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user):
        return
    text = update.effective_message.text or update.effective_message.caption or "[非文本消息]"
    await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.effective_message.reply_text("你不是管理员，无权广播。")
        return
    if not context.args:
        await update.effective_message.reply_text("请提供广播内容。用法：/broadcast 内容")
        return
    text = " ".join(context.args)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"【管理员广播】\n\n{text}")
    await update.effective_message.reply_text("广播已发送。")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.effective_message.reply_text("你不是管理员，无权禁言。")
        return
    if not context.args:
        await update.effective_message.reply_text("请提供要禁止的用户id或用户名或昵称。用法：/ban 用户")
        return
    user_identifier = context.args[0].lower()
    banned_users.add(user_identifier)
    save_banned(banned_users)
    await update.effective_message.reply_text(f"已禁止用户：{user_identifier}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.effective_message.reply_text("你不是管理员，无权解禁。")
        return
    if not context.args:
        await update.effective_message.reply_text("请提供要解除禁止的用户id或用户名或昵称。用法：/unban 用户")
        return
    user_identifier = context.args[0].lower()
    if user_identifier in banned_users:
        banned_users.remove(user_identifier)
        save_banned(banned_users)
        await update.effective_message.reply_text(f"已解除禁止用户：{user_identifier}")
    else:
        await update.effective_message.reply_text(f"用户 {user_identifier} 不在禁止列表。")

async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user):
        return
    # 只转发非命令消息
    if update.message and not update.message.text.startswith("/"):
        await handle_message(update, context)

# 创建 Application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 注册命令处理器
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(CommandHandler("ban", ban))
application.add_handler(CommandHandler("unban", unban))
# 注册消息处理器
application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), echo_handler))

# FastAPI webhook入口
@app.post(WEBHOOK_PATH)
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Bot is running."}
