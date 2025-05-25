import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# 配置
BOT_TOKEN = os.getenv("BOT_TOKEN", "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://telegram-bot-p5yt.onrender.com")
CHANNEL_ID = -1001763041158
ADMIN_IDS = [7848870377]
VIP_FILE = "vip_users.json"
AUTO_APPROVE_VIP = True
PORT = int(os.getenv("PORT", 8443))

# 加载/保存会员数据
def load_vip():
    try:
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_vip(vip_users):
    with open(VIP_FILE, "w") as f:
        json.dump(vip_users, f)

vip_users = load_vip()

# 处理 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用匿名投稿机器人！")

# 接收普通用户消息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message.text

    if AUTO_APPROVE_VIP and user_id in vip_users:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
        await update.message.reply_text("✅ 已自动匿名发送到频道")
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ 通过", callback_data=f"approve:{user_id}"),
             InlineKeyboardButton("❌ 拒绝", callback_data=f"reject:{user_id}")]
        ])
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=f"新投稿来自 {user_id}：\n\n{message}", reply_markup=keyboard)
        await update.message.reply_text("🕓 已提交审核，请等待管理员处理")

# 审核按钮处理
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    action, user_id_str = data.split(":")
    user_id = int(user_id_str)

    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("⛔ 无权限")
        return

    original_msg = query.message.text.split("：\n\n", 1)[-1]

    if action == "approve":
        await context.bot.send_message(chat_id=CHANNEL_ID, text=original_msg)
        await context.bot.send_message(chat_id=user_id, text="✅ 你的投稿已通过并发布")
        await query.edit_message_text("✅ 已发布")
    elif action == "reject":
        await context.bot.send_message(chat_id=user_id, text="❌ 你的投稿未通过审核")
        await query.edit_message_text("❌ 已拒绝")

# 添加会员
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("请提供用户ID或@用户名")
        return

    identifier = context.args[0]
    if identifier.startswith("@"):
        user = await context.bot.get_chat(identifier)
        user_id = user.id
    else:
        user_id = int(identifier)

    if user_id not in vip_users:
        vip_users.append(user_id)
        save_vip(vip_users)
        await update.message.reply_text(f"✅ 已添加 {user_id} 为会员")
    else:
        await update.message.reply_text("用户已是会员")

# 删除会员
async def del_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("请提供用户ID或@用户名")
        return

    identifier = context.args[0]
    if identifier.startswith("@"):
        user = await context.bot.get_chat(identifier)
        user_id = user.id
    else:
        user_id = int(identifier)

    if user_id in vip_users:
        vip_users.remove(user_id)
        save_vip(vip_users)
        await update.message.reply_text(f"❌ 已移除 {user_id} 的会员资格")
    else:
        await update.message.reply_text("用户不是会员")

# 开关自动审核
async def enable_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_APPROVE_VIP
    if update.effective_user.id in ADMIN_IDS:
        AUTO_APPROVE_VIP = True
        await update.message.reply_text("✅ 已启用会员免审核")

async def disable_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_APPROVE_VIP
    if update.effective_user.id in ADMIN_IDS:
        AUTO_APPROVE_VIP = False
        await update.message.reply_text("⛔ 已暂停会员免审核")

# 广播
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("请提供广播内容")
        return

    content = " ".join(context.args)
    sent = 0
    for user_id in vip_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=content)
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(f"📣 广播完成，成功发送给 {sent} 名会员")

# 启动 Webhook 应用
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("delvip", del_vip))
    app.add_handler(CommandHandler("enablevip", enable_vip))
    app.add_handler(CommandHandler("disablevip", disable_vip))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
