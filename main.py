import json
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os

# === 配置 ===
BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158  # 替换为你的频道 ID
ADMIN_ID = 7848870377        # 替换为你的管理员 ID
BLACKLIST_FILE = "blacklist.json"

app = FastAPI()
bot = Bot(token=BOT_TOKEN)


# === 黑名单相关函数 ===
def load_blacklist():
    try:
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(blacklist, f)

def is_blacklisted(user_id, username):
    blacklist = load_blacklist()
    return str(user_id) in blacklist or (username and username.lower() in blacklist)


# === 处理用户消息 ===
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username.lower() if user.username else None

    if is_blacklisted(user_id, username):
        await update.message.reply_text("您已被禁言，无法使用本 Bot。")
        return

    if update.message:
        if update.message.text:
            await bot.send_message(chat_id=CHANNEL_ID, text=update.message.text)
        elif update.message.photo:
            await bot.send_photo(chat_id=CHANNEL_ID, photo=update.message.photo[-1].file_id, caption=update.message.caption or "")
        elif update.message.video:
            await bot.send_video(chat_id=CHANNEL_ID, video=update.message.video.file_id, caption=update.message.caption or "")
        elif update.message.document:
            await bot.send_document(chat_id=CHANNEL_ID, document=update.message.document.file_id, caption=update.message.caption or "")
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text="[收到一个不支持的消息类型]")

# === 管理员命令：添加/移除黑名单 ===
async def add_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("用法：/ban 用户ID 或 @用户名")
        return

    blacklist = load_blacklist()
    target = context.args[0].lower()
    if target not in blacklist:
        blacklist.append(target)
        save_blacklist(blacklist)
        await update.message.reply_text(f"{target} 已加入黑名单")
    else:
        await update.message.reply_text(f"{target} 已在黑名单中")

async def remove_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("用法：/unban 用户ID 或 @用户名")
        return

    blacklist = load_blacklist()
    target = context.args[0].lower()
    if target in blacklist:
        blacklist.remove(target)
        save_blacklist(blacklist)
        await update.message.reply_text(f"{target} 已从黑名单移除")
    else:
        await update.message.reply_text(f"{target} 不在黑名单中")


# === Webhook 接收入口 ===
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return {"ok": True}


# === 启动应用（使用 Webhook） ===
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), forward_message))
application.add_handler(CommandHandler("ban", add_blacklist))
application.add_handler(CommandHandler("unban", remove_blacklist))
