import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158
ADMIN_IDS = [7848870377]

VIP_FILE = 'vip_users.json'
CONFIG_FILE = 'config.json'
USERS_FILE = 'users.json'

# --- 文件操作 ---
def load_vip_users():
    try:
        with open(VIP_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_vip_users(vips):
    with open(VIP_FILE, 'w') as f:
        json.dump(vips, f)

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"vip_enabled": True}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# --- 通用工具 ---
async def delete_message(context):
    await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)

# --- 机器人命令 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in load_users():
        users = load_users()
        users.append(user_id)
        save_users(users)

    is_admin = user_id in ADMIN_IDS

    text = (
        "🎉 欢迎使用匿名投稿 Bot！\n\n"
        "📨 直接发送文字内容给我即可投稿。\n"
        "✅ 管理员审核通过后将 *匿名发布到频道*。\n\n"
        "🌟 成为会员可免审核，消息自动发布。\n"
        "🔐 输入 /buyvip 查看如何充值会员。"
    )

    if is_admin:
        text += (
            "\n\n📣 *管理员命令：*\n"
            "/addvip 用户ID/@用户名 - 添加会员\n"
            "/delvip 用户ID/@用户名 - 删除会员\n"
            "/enablevip - 启用会员免审核机制\n"
            "/disablevip - 暂停会员免审核机制\n"
            "/broadcast 内容 - 广播消息给所有用户"
        )

    msg = await update.message.reply_markdown(text)
    context.job_queue.run_once(delete_message, 60, chat_id=msg.chat_id, data=msg.message_id)

async def buyvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("请联系管理员 @Haohaoss 充值成为会员。")
    context.job_queue.run_once(delete_message, 60, chat_id=msg.chat_id, data=msg.message_id)

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/addvip 用户ID 或 @用户名")
        return
    user = context.args[0]
    vips = load_vip_users()
    if user not in vips:
        vips.append(user)
        save_vip_users(vips)
        await update.message.reply_text(f"{user} 已添加为会员。")
    else:
        await update.message.reply_text(f"{user} 已是会员。")

async def del_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/delvip 用户ID 或 @用户名")
        return
    user = context.args[0]
    vips = load_vip_users()
    if user in vips:
        vips.remove(user)
        save_vip_users(vips)
        await update.message.reply_text(f"{user} 已移除会员。")
    else:
        await update.message.reply_text(f"{user} 不是会员。")

async def disable_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    config = load_config()
    config["vip_enabled"] = False
    save_config(config)
    msg = await update.message.reply_text("✅ 已暂停会员免审核机制，所有消息将进入人工审核。")
    context.job_queue.run_once(delete_message, 60, chat_id=msg.chat_id, data=msg.message_id)

async def enable_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    config = load_config()
    config["vip_enabled"] = True
    save_config(config)
    msg = await update.message.reply_text("✅ 已启用会员免审核机制，VIP 用户将自动发布。")
    context.job_queue.run_once(delete_message, 60, chat_id=msg.chat_id, data=msg.message_id)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/broadcast 内容")
        return
    message = ' '.join(context.args)
    users = load_users()
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=message)
            count += 1
        except:
            pass
    await update.message.reply_text(f"已向 {count} 名用户发送消息。")

# --- 消息处理 ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    vips = load_vip_users()
    config = load_config()
    user_id = str(user.id)
    username = f"@{user.username}" if user.username else user_id

    if user.id not in load_users():
        users = load_users()
        users.append(user.id)
        save_users(users)

    if config.get("vip_enabled", True) and (user_id in vips or username in vips):
        await context.bot.send_message(chat_id=CHANNEL_ID, text=update.message.text)
        msg = await update.message.reply_text("您的消息已匿名发布到频道。")
        context.job_queue.run_once(delete_message, 60, chat_id=msg.chat_id, data=msg.message_id)
    else:
        for admin_id in ADMIN_IDS:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("通过", callback_data=f"approve|{update.message.text}|{user.id}"),
                InlineKeyboardButton("拒绝", callback_data=f"reject|{user.id}")
            ]])
            await context.bot.send_message(chat_id=admin_id, text=f"收到投稿：\n\n{update.message.text}", reply_markup=keyboard)
        msg = await update.message.reply_text("您的消息已提交审核，请等待管理员处理。")
        context.job_queue.run_once(delete_message, 60, chat_id=msg.chat_id, data=msg.message_id)

# --- 审核按钮回调 ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    action = data[0]

    if action == "approve":
        text, user_id = data[1], int(data[2])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await context.bot.send_message(chat_id=user_id, text="您的投稿已通过审核并发布到频道。")
        await query.edit_message_text("✅ 已通过，消息已发布。")
    elif action == "reject":
        user_id = int(data[1])
        await context.bot.send_message(chat_id=user_id, text="❌ 您的投稿未通过审核。")
        await query.edit_message_text("已拒绝。")

# --- 启动 Bot ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buyvip", buyvip))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("delvip", del_vip))
    app.add_handler(CommandHandler("disablevip", disable_vip))
    app.add_handler(CommandHandler("enablevip", enable_vip))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
