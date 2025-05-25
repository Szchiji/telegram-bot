import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# === 环境变量 ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("请确保环境变量 BOT_TOKEN 和 WEBHOOK_URL 已正确设置")

# === 频道和管理员配置 ===
CHANNEL_ID = -1001763041158
ADMIN_IDS = [7848870377]

# === 会员数据文件路径 ===
MEMBERS_FILE = "members.json"


# === 会员数据处理 ===
def load_members():
    if os.path.exists(MEMBERS_FILE):
        with open(MEMBERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_members(members):
    with open(MEMBERS_FILE, "w") as f:
        json.dump(members, f)

# === 命令 ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用匿名投稿Bot！")

async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/addmember <user_id>")
        return
    user_id = int(context.args[0])
    members = load_members()
    if user_id not in members:
        members.append(user_id)
        save_members(members)
        await update.message.reply_text(f"已添加会员：{user_id}")
    else:
        await update.message.reply_text("该用户已是会员")

async def remove_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/removemember <user_id>")
        return
    user_id = int(context.args[0])
    members = load_members()
    if user_id in members:
        members.remove(user_id)
        save_members(members)
        await update.message.reply_text(f"已移除会员：{user_id}")
    else:
        await update.message.reply_text("该用户不是会员")

# === 普通用户投稿 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    members = load_members()

    if user_id in members:
        await context.bot.send_message(CHANNEL_ID, text=message.text)
        await message.reply_text("✅ 已匿名发送")
    else:
        # 保存待审消息和用户ID
        context.user_data["pending_message"] = message.text
        keyboard = [
            [
                InlineKeyboardButton("✅ 通过", callback_data=f"approve:{user_id}"),
                InlineKeyboardButton("❌ 拒绝", callback_data=f"reject:{user_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"用户 {user_id} 投稿内容：\n\n{message.text}",
                reply_markup=reply_markup,
            )
        await message.reply_text("⏳ 投稿已提交，等待管理员审核。")

# === 回调处理 ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    action, user_id_str = data.split(":")
    user_id = int(user_id_str)

    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("你不是管理员，无权操作。")
        return

    if action == "approve":
        msg = context.user_data.get("pending_message", "")
        if msg:
            await context.bot.send_message(CHANNEL_ID, text=msg)
            await context.bot.send_message(chat_id=user_id, text="✅ 你的投稿已通过审核并匿名发布。")
            await query.edit_message_text("✅ 已通过并发布")
    elif action == "reject":
        await context.bot.send_message(chat_id=user_id, text="❌ 你的投稿未通过审核。")
        await query.edit_message_text("❌ 已拒绝投稿")

# === 启动 ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addmember", add_member))
    app.add_handler(CommandHandler("removemember", remove_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
