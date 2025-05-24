from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'  # 频道 ID

# 添加多个审核人员的 Telegram 用户 ID
ADMIN_IDS = [7848870377]  # 你的 Telegram 用户 ID

# 创建内联按钮（审核按钮）
def create_approval_buttons(message_id):
    keyboard = [
        [InlineKeyboardButton("通过", callback_data=f"approve_{message_id}")],
        [InlineKeyboardButton("拒绝", callback_data=f"reject_{message_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# 处理所有用户的消息，转发给管理员审核
async def send_for_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_text = update.message.text  # 获取消息文本
        user_id = update.message.from_user.id  # 获取用户的 ID
        message_id = update.message.message_id  # 获取消息 ID

        # 发送消息到所有审核人员
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"新消息来自 @{update.message.from_user.username}（ID：{user_id}）：\n\n{message_text}\n\n是否批准该消息？",
                reply_markup=create_approval_buttons(message_id)  # 添加按钮
            )
        print(f"转发给审核人员：{message_text}")  # 记录消息

# 处理按钮点击事件
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message_id = int(query.data.split("_")[1])  # 获取消息 ID
    action = query.data.split("_")[0]  # 获取操作（approve 或 reject）

    if action == "approve":
        # 如果审核通过，转发到频道
        await context.bot.forward_message(
            chat_id=CHANNEL_ID,
            from_chat_id=query.message.chat_id,
            message_id=message_id
        )
        await query.answer("消息已批准，已转发到频道！")
    elif action == "reject":
        # 如果拒绝，回复用户并不转发消息
        await query.answer("消息被拒绝，未转发到频道！")

    # 删除按钮（避免重复点击）
    await query.edit_message_reply_markup(reply_markup=None)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 处理所有消息
    app.add_handler(MessageHandler(filters.ALL, send_for_approval))  # 所有用户发送的消息都会转发给管理员审核

    # 处理按钮点击
    app.add_handler(CallbackQueryHandler(button_handler))  # 处理按钮点击

    print("Bot is running...")
    app.run_polling()


