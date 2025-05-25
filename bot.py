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

BOT_TOKEN = "8092070129:AAGxrcDxMFniPLjNnZ4eNYd-Mtq9JBra-60"
CHANNEL_ID = -1001763041158
ADMIN_IDS = [7848870377]
WEBHOOK_DOMAIN = "telegram-bot-se3s.onrender.com"

VIP_FILE = "vip_users.json"

vip_mode = True  # 会员机制开关


def load_vip_users():
    try:
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_vip_users(vips):
    with open(VIP_FILE, "w") as f:
        json.dump(vips, f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    msg = (
        "欢迎使用投稿 Bot！\n\n"
        "发送消息给我将提交管理员审核，通过后将匿名发到频道。\n"
        "成为会员可跳过审核，自动发布。\n"
        "输入 /buyvip 了解如何成为会员。\n"
        "管理员命令：\n"
        "/addvip 用户ID 或 @用户名\n"
        "/delvip 用户ID 或 @用户名\n"
        "/broadcast 内容\n"
        "/pausevip 暂停会员机制\n"
        "/startvip 开启会员机制"
    )
    await update.message.reply_text(msg)


async def buyvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("请联系管理员 @Haohaoss 充值成为会员。")


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


async def pause_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global vip_mode
    if update.effective_user.id not in ADMIN_IDS:
        return
    vip_mode = False
    await update.message.reply_text("会员机制已暂停，所有用户投稿都需审核。")


async def start_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global vip_mode
    if update.effective_user.id not in ADMIN_IDS:
        return
    vip_mode = True
    await update.message.reply_text("会员机制已开启，会员投稿自动发布。")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("用法：/broadcast 你的消息内容")
        return
    msg = " ".join(context.args)
    vips = load_vip_users()
    sent = 0
    for user in vips:
        try:
            if user.startswith("@"):
                await context.bot.send_message(chat_id=user, text=f"管理员广播：\n\n{msg}")
            else:
                await context.bot.send_message(chat_id=int(user), text=f"管理员广播：\n\n{msg}")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"广播消息已发送给 {sent} 位会员。")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    vips = load_vip_users()
    user_id_str = str(user.id)
    username = f"@{user.username}" if user.username else user_id_str

    if vip_mode and (user_id_str in vips or username in vips):
        await context.bot.send_message(chat_id=CHANNEL_ID, text=update.message.text)
        msg = await update.message.reply_text("您的消息已匿名发布到频道。")
        await context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id),
            when=60,
        )
    else:
        for admin_id in ADMIN_IDS:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "通过", callback_data=f"approve|{update.message.text}|{user.id}"
                        )
                    ],
                    [InlineKeyboardButton("拒绝", callback_data=f"reject|{user.id}")],
                ]
            )
            await context.bot.send_message(
                chat_id=admin_id, text=f"收到投稿：\n\n{update.message.text}", reply_markup=keyboard
            )
        msg = await update.message.reply_text("您的消息已提交审核，请等待管理员处理。")
        await context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id),
            when=60,
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]

    if action == "approve":
        text, user_id = data[1], int(data[2])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await context.bot.send_message(chat_id=user_id, text="您的投稿已通过审核并发布到频道。")
        await query.edit_message_text("已通过，消息已发布。")
    elif action == "reject":
        user_id = int(data[1])
        await context.bot.send_message(chat_id=user_id, text="您的投稿未通过审核。")
        await query.edit_message_text("已拒绝。")


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buyvip", buyvip))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CommandHandler("delvip", del_vip))
    app.add_handler(CommandHandler("pausevip", pause_vip))
    app.add_handler(CommandHandler("startvip", start_vip))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    WEBHOOK_PATH = f"/bot{BOT_TOKEN}"
    WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

    await app.bot.set_webhook(WEBHOOK_URL)

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=WEBHOOK_URL,  # 正确使用 webhook_url 参数
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

