from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'
ADMIN_IDS = [7848870377]

# 缓存用户原始消息文本
pending_messages = {}

# 创建审核按钮
def create_approval_buttons(msg_key):
    keyboard = [
        [InlineKeyboardButton("通过", callback_data=f"approve_{msg_key}")],
        [InlineKeyboardButton("拒绝", callback_data=f"reject_{msg_key}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# 用户发来消息时：发送到管理员审核
async def send_for_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user = update.message.from_user
        user_chat_id = update.message.chat_id
        user_message_id = update.message.message_id
        msg_text = update.message.text or "<非文本消息>"
        msg_key = f"{user_chat_id}_{user_message_id}"

        # 缓存消息文本
        pending_messages[msg_key] = msg_text

        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"用户 @{user.username or user.first_name} 的消息：\n\n{msg_text}",
                reply_markup=create_approval_buttons(msg_key)
            )

# 管理员点击按钮：处理审核结果
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_") or data.startswith("reject_"):
        action, msg_key = data.split("_", 1)

        if msg_key in pending_messages:
            msg_text = pending_messages.pop(msg_key)

            if action == "approve":
                try:
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=msg_text
                    )
                    await query.edit_message_text("消息已通过并匿名发到频道。")
                except Exception as e:
                    await query.edit_message_text(f"发送失败：{e}")
            else:
                await query.edit_message_text("消息已拒绝。")
        else:
            await query.edit_message_text("找不到原始消息，可能已处理过。")

if name == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_for_approval))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
