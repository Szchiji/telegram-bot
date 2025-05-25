import os
import json
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Telegram 配置
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377
DATA_FILE = "vip_data.json"

# 读取/保存会员数据
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"vip_users": [], "vip_enabled": True}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 权限与会员判断
def is_admin(user_id): return user_id == ADMIN_ID
def is_vip(user_id): return user_id in data.get("vip_users", [])

# 自动删除消息
async def auto_delete_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

# 指令：/start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = "欢迎使用投稿机器人！\n\n"
    if is_admin(uid):
        text += (
            "👑 管理命令：\n"
            "/addvip 用户ID/@用户名\n"
            "/delvip 用户ID/@用户名\n"
            "/enablevip\n"
            "/disablevip\n"
            "/broadcast 内容\n"
        )
    elif is_vip(uid) and data.get("vip_enabled", True):
        text += "💎 您是会员，投稿将自动发布。"
    else:
        text += "您可以投稿，投稿由管理员审核发布。\n点击下方成为会员免审核："

    keyboard = [
        [InlineKeyboardButton("📨 投稿", callback_data="submit")],
        [InlineKeyboardButton("💎 成为会员", url="https://t.me/Haohaoss")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# 投稿按钮回调
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("请直接发送文字、图片或视频投稿内容。")

# 管理命令
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("无权限")
    if not context.args:
        return await update.message.reply_text("格式：/addvip 用户ID/@用户名")
    target = context.args[0]
    try:
        target_id = int(target) if not target.startswith("@") else (await context.bot.get_chat(target)).id
        if target_id in data["vip_users"]:
            return await update.message.reply_text("该用户已是会员。")
        data["vip_users"].append(target_id)
        save_data(data)
        await update.message.reply_text(f"已添加会员：{target_id}")
    except:
        await update.message.reply_text("添加失败，检查用户是否与 Bot 有交集。")

async def delvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("无权限")
    if not context.args:
        return await update.message.reply_text("格式：/delvip 用户ID/@用户名")
    target = context.args[0]
    try:
        target_id = int(target) if not target.startswith("@") else (await context.bot.get_chat(target)).id
        if target_id in data["vip_users"]:
            data["vip_users"].remove(target_id)
            save_data(data)
            await update.message.reply_text(f"已移除会员：{target_id}")
        else:
            await update.message.reply_text("该用户不是会员。")
    except:
        await update.message.reply_text("移除失败")

async def enablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        data["vip_enabled"] = True
        save_data(data)
        await update.message.reply_text("已启用免审核。")

async def disablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        data["vip_enabled"] = False
        save_data(data)
        await update.message.reply_text("已暂停免审核。")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = " ".join(context.args)
    if not msg: return await update.message.reply_text("请输入内容")
    count = 0
    for uid in data["vip_users"]:
        try:
            await context.bot.send_message(uid, f"📢 广播消息：\n\n{msg}")
            count += 1
        except: pass
    await update.message.reply_text(f"成功发送给 {count} 位会员")

# 会员自动发帖
async def forward_to_channel_anon(context: ContextTypes.DEFAULT_TYPE, msg):
    if msg.text:
        await context.bot.send_message(CHANNEL_ID, msg.text)
    elif msg.photo:
        await context.bot.send_photo(CHANNEL_ID, msg.photo[-1].file_id, caption=msg.caption or "")
    elif msg.video:
        await context.bot.send_video(CHANNEL_ID, msg.video.file_id, caption=msg.caption or "")

# 待审核缓存
pending_messages = {}

# 普通用户投稿
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id): return
    msg = update.message
    if is_vip(user_id) and data.get("vip_enabled", True):
        await forward_to_channel_anon(context, msg)
        sent = await msg.reply_text("感谢您的投稿，已自动发布！")
        asyncio.create_task(auto_delete_message(context, sent.chat_id, sent.message_id))
        return

    content_type = "text" if msg.text else "photo" if msg.photo else "video" if msg.video else None
    if not content_type:
        return await msg.reply_text("仅支持文字、图片、视频投稿。")

    file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id if msg.video else None
    content = msg.text or msg.caption or ""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 通过", callback_data=f"approve_{msg.message_id}"),
        InlineKeyboardButton("❌ 拒绝", callback_data=f"reject_{msg.message_id}")
    ]])

    sent = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"新投稿（用户 {user_id}）:\n\n{content}" if content_type == "text" else "",
        reply_markup=keyboard
    ) if content_type == "text" else await context.bot.send_photo(
        ADMIN_ID, file_id, caption=f"用户 {user_id}", reply_markup=keyboard
    ) if content_type == "photo" else await context.bot.send_video(
        ADMIN_ID, file_id, caption=f"用户 {user_id}", reply_markup=keyboard
    )

    pending_messages[str(sent.message_id)] = {
        "user_id": user_id,
        "content_type": content_type,
        "content": content,
        "file_id": file_id,
    }
    await msg.reply_text("您的投稿已提交，等待管理员审核。")

# 审核回调
async def approve_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return await query.answer("无权限", show_alert=True)

    action, msg_id = query.data.split("_")
    msg_info = pending_messages.pop(msg_id, None)
    if not msg_info:
        return await query.answer("投稿不存在或已处理", show_alert=True)

    uid = msg_info["user_id"]
    ctype = msg_info["content_type"]
    content = msg_info["content"]
    fid = msg_info["file_id"]

    if action == "approve":
        await forward_to_channel_anon(context, Update(message=update.effective_message))
        await context.bot.send_message(uid, "✅ 投稿已通过并发布")
        try:
            if ctype in ("photo", "video"):
                await query.edit_message_caption("✅ 已通过")
            else:
                await query.edit_message_text("✅ 已通过")
        except: pass
    else:
        await context.bot.send_message(uid, "❌ 投稿未通过审核")
        try:
            if ctype in ("photo", "video"):
                await query.edit_message_caption("❌ 已拒绝")
            else:
                await query.edit_message_text("❌ 已拒绝")
        except: pass
    await query.answer()

# FastAPI 应用
app = FastAPI()
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("addvip", addvip))
telegram_app.add_handler(CommandHandler("delvip", delvip))
telegram_app.add_handler(CommandHandler("enablevip", enablevip))
telegram_app.add_handler(CommandHandler("disablevip", disablevip))
telegram_app.add_handler(CommandHandler("broadcast", broadcast))
telegram_app.add_handler(CallbackQueryHandler(approve_reject_callback, pattern="^(approve|reject)_"))
telegram_app.add_handler(CallbackQueryHandler(button_handler, pattern="^submit$"))
telegram_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_user_message))

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await telegram_app.update_queue.put(Update.de_json(data, telegram_app.bot))
    return {"ok": True}
