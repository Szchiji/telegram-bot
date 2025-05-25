import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ===== 配置 =====
BOT_TOKEN = '你的-BOT-TOKEN'
CHANNEL_ID = -1001763041158
ADMIN_IDS = [7848870377]
VIP_FILE = 'vip_users.json'

# ===== VIP 数据 =====
def load_vip_users():
    if not os.path.exists(VIP_FILE):
        with open(VIP_FILE, 'w') as f:
            json.dump([], f)
    with open(VIP_FILE, 'r') as f:
        return json.load(f)

def save_vip_users(vips):
    with open(VIP_FILE, 'w') as f:
        json.dump(vips, f)

def is_vip(user_id):
    vips = load_vip_users()
    return user_id in vips

# ===== 审核缓存 =====
pending_messages = {}  # key: msg_key, value: {'user_id': ..., 'text': ...}

def create_approval_buttons(msg_key):
    keyboard = [
        [InlineKeyboardButton("✅ 通过", callback_data=f"approve_{msg_key}")],
        [InlineKeyboardButton("❌ 拒绝", callback_data=f"reject_{msg_key}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== 用户发消息 =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_text = update.message.text or "<非文本消息>"

    if is_vip(user_id):
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg_text)
    else:
        msg_key = f"{user_id}_{update.message.message_id}"
        pending_messages[msg_key] = {'user_id': user_id, 'text': msg_text}

        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"来自 @{update.effective_user.username or update.effective_user.first_name} 的消息：\n\n{msg_text}",
                reply_markup=create_approval_buttons(msg_key)
            )

# ===== 审核处理 =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_") or data.startswith("reject_"):
        action, msg_key = data.split("_", 1)

        if msg_key not in pending_messages:
            await query.edit_message_text("消息已处理或不存在。")
            return

        info = pending_messages.pop(msg_key)
        user_id = info['user_id']
        msg_text = info['text']

        if action == "approve":
            await context.bot.send_message(chat_id=CHANNEL_ID, text=msg_text)
            await query.edit_message_text("消息已通过，已匿名发到频道。")
        else:
            await context.bot.send_message(chat_id=user_id, text="你的消息未通过审核。")
            await query.edit_message_text("已拒绝该消息。")

# ===== 管理员添加 VIP =====
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("用法：/addvip 用户ID 或 @用户名")
        return

    identifier = context.args[0]
    try:
        if identifier.startswith('@'):
            user = await context.bot.get_chat(identifier)
            user_id = user.id
        else:
            user_id = int(identifier)

        vips = load_vip_users()
        if user_id not in vips:
            vips.append(user_id)
            save_vip_users(vips)
            await update.message.reply_text("添加会员成功。")
        else:
            await update.message.reply_text("该用户已是会员。")
    except Exception as e:
        await update.message.reply_text(f"添加失败：{e}")

# ===== 管理员删除 VIP =====
async def del_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("用法：/delvip 用户ID 或 @用户名")
        return

    identifier = context.args[0]
    try:
        if identifier.startswith('@'):
            user = await context.bot.get_chat(identifier)
            user_id = user.id
        else:
            user_id = int(identifier)

        vips = load_vip_users()
        if user_id in vips:
            vips.remove(user_id)
            save_vip_users(vips)
            await update.message.reply_text("已移除会员。")
        else:
            await update.message.reply_text("该用户不是会员。")
    except Exception as e:
        await update.message.reply_text(f"移除失败：{e}")

# ===== 用户购买会员入口 =====
async def buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "如需开通会员，请联系管理员转账。\n"
        "价格：10U/月 支付宝口令 100/月\n"
        "请联系 @choujiangmissbot\n"
        "开通后享受免审核特权。"
    )
    await update.message.reply_text(text)

# ===== 启动程序 =====
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("delvip", del_vip))
    app.add_handler(CommandHandler("buyvip", buy_vip))

    app.run_polling()