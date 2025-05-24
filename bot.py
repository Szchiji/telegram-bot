from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json

BOT_TOKEN = '8092070129:AAFuE3WBP6z7YyFpY1uIE__WujCOv6jd-oI'
ADMIN_IDS = [7848870377]  # 管理员的用户 ID

# 存储触发词和自动回复内容的文件路径
REPLY_FILE = 'trigger_replies.json'


# 从文件加载触发词和自动回复内容
def load_trigger_replies():
    try:
        with open(REPLY_FILE, 'r') as f:
            data = json.load(f)
            return data.get('trigger_replies', {})
    except FileNotFoundError:
        return {}


# 保存触发词和自动回复内容到文件
def save_trigger_replies(trigger_replies):
    with open(REPLY_FILE, 'w') as f:
        json.dump({'trigger_replies': trigger_replies}, f)


# 处理设置触发词和自动回复的命令
async def set_trigger_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 仅允许管理员使用该命令
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("你没有权限使用此命令。")
        return

    if len(context.args) < 2:
        await update.message.reply_text("请提供触发词和回复内容，例如：/settrigger 响应 你好，世界！")
        return

    trigger_word = context.args[0]  # 触发词
    reply_message = ' '.join(context.args[1:])  # 自动回复内容

    # 获取当前设置的触发词和回复内容
    trigger_replies = load_trigger_replies()
    
    # 更新触发词和自动回复内容
    trigger_replies[trigger_word] = reply_message
    save_trigger_replies(trigger_replies)

    await update.message.reply_text(f"已设置触发词 '{trigger_word}' 的自动回复：\n{reply_message}")


# 处理所有用户的消息，匹配触发词并回复
async def check_trigger_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 获取当前设置的触发词和自动回复内容
    trigger_replies = load_trigger_replies()
    
    # 获取用户发送的消息文本
    message_text = update.message.text.lower()  # 将消息文本转换为小写以进行不区分大小写的匹配
    
    # 检查用户的消息是否包含在触发词列表中
    for trigger, reply in trigger_replies.items():
        if trigger.lower() in message_text:  # 如果用户消息中包含触发词
            await update.message.reply_text(reply)  # 发送自动回复
            print(f"触发词 '{trigger}' 匹配，已自动回复：{reply}")
            break  # 匹配到第一个触发词后停止检查


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 添加管理员设置触发词和自动回复的命令
    app.add_handler(CommandHandler("settrigger", set_trigger_reply))

    # 处理所有用户的消息并检查是否匹配触发词
    app.add_handler(MessageHandler(filters.ALL, check_trigger_and_reply))

    print("Bot is running...")
    app.run_polling()
