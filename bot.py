from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
CHANNEL_ID = '@sixuexi'

# 添加多个审核人员的 Telegram 用户 ID
ADMIN_IDS = [7848870377, 1234567890]  # 在这里添加更多审核人员的 ID

# 将消息转发给所有审核人员
async def send_for_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_text = update.message.text  # 获取消息文本
        user_id = update.message.from_user.id  # 获取用户的 ID

        # 发送消息到所有审核人员
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"新消息来自 @{update.message.from_user.username}（ID：{user_id}）：\n\n{message_text}\n\n是否通过？"
            )
        print(f"转发给审核人员：{message_text}")  # 记录消息

# 审核通过后才转发到频道
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_text = update.message.text  # 获取消息文本

        # 这里可以设置审核逻辑，比如检查是否符合某些规则
        if True:  # 修改此处为你审核通过的条件
            await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            print(f"转发到频道：{message_text}")  # 记录消息
        else:
            await update.message.reply_text("消息未通过审核！")  # 如果不通过审核
            print(f"拒绝消息：{message_text}")  # 记录拒绝的消息

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, send_for_approval))  # 先转发给所有审核人员
    print("Bot is running...")
    app.run_polling()
