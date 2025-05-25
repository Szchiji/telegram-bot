import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158
ADMIN_IDS = [7848870377]

VIP_FILE = 'vip_users.json'

def load_vip_users():
    try:
        with open(VIP_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_vip_users(vips):
    with open(VIP_FILE, 'w') as f:
        json.dump(vips, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "欢迎使用投稿 Bot！\n\n"
        "您可以发送消息给我，我将提交管理员审核，通过后将匿名发到频道。\n\n"
        "成为会员可跳过审核，自动匿名发布。\n"
        "输入 /buyvip 查看成为会员的方式。"
    )
    await update.message.reply_text(msg)

async def buyvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("请联系管理员充值成为会员。管理员 Telegram ID：@Haohaoss")

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/addvip 用户ID或@用户名")
        return
    user = context.args[0]
    vips = load_vip_users()
    if user not in vips:
        vips.append(user)
        save_vip_users(vips)
        await update.message.reply_text(f"{user} 已被添加为会员。")
    else:
        await update.message.reply_text(f"{user} 已是会员。")

async def del_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/delvip 用户ID或@用户名")
        return
    user = context.args[0]
    vips = load_vip_users()
    if user in vips:
        vips.remove(user)
        save_vip_users(vips)
        await update.message.reply_text(f"{user} 已被移除会员。")
    else:
        await update.message.reply_text(f"{user} 不是会员。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    vips = load_vip_users()
    user_id = str(user.id)
    username = f"@{user.username}" if user.username else user_id

    if user_id in vips or username in vips:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=update.message.text)
        await update.message.reply_text("您的消息已匿名发布到频道。")
    else:
        for admin_id in ADMIN_IDS:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("通过", callback_data=f"approve|{update.message.text}|{user.id}")],
                [InlineKeyboardButton("拒绝", callback_data=f"reject|{user.id}")]
            ])
            await context.bot.send_message(chat_id=admin_id, text=f"收到用户投稿：\n\n{update.message.text}", reply_markup=keyboard)
        await update.message.reply_text("您的消息已提交审核，请等待管理员处理。")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    action = data[0]

    if action == "approve":
        text, user_id = data[1], int(data[2])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await context.bot.send_message(chat_id=user_id, text="您的投稿已通过审核并匿名发布到频道。")
        await query.edit_message_text("已通过并发布到频道。")
    elif action == "reject":
        user_id = int(data[1])
        await context.bot.send_message(chat_id=user_id, text="您的投稿未通过审核，请重新尝试，请联系管理员。")
        await query.edit_message_text("已拒绝。")

# ✅ Webhook 启动配置
async def set_webhook(app):
    await app.bot.set_webhook("https://telegram-bot-g6id.onrender.com/webhook")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buyvip", buyvip))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("delvip", del_vip))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_path="/webhook",
        on_startup=set_webhook
    )

if __name__ == "__main__":
    main()