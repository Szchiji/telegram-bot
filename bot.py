import os
import json
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatAction,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 频道ID，管理员ID
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377

# 数据文件，用于存储会员列表和状态
DATA_FILE = "vip_data.json"

# 读取或初始化数据
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"vip_users": [], "vip_enabled": True}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("请确保环境变量 BOT_TOKEN 和 WEBHOOK_URL 已正确设置")

# 判断是否管理员
def is_admin(user_id):
    return user_id == ADMIN_ID

# 判断是否VIP会员
def is_vip(user_id):
    return user_id in data.get("vip_users", [])

# 自动删除bot发出消息的函数
async def auto_delete_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    is_user_vip = is_vip(user_id)

    keyboard = [
        [InlineKeyboardButton("📨 投稿", callback_data="submit")],
        [InlineKeyboardButton("💎 成为会员", url="https://t.me/Haohaoss")],
    ]

    text = "欢迎使用投稿机器人！\n\n"

    if is_user_admin:
        text += (
            "👑 您是管理员，管理命令如下：\n"
            "/addvip 用户ID/@用户名 - 添加会员\n"
            "/delvip 用户ID/@用户名 - 删除会员\n"
            "/enablevip - 启用会员免审核机制\n"
            "/disablevip - 暂停会员免审核机制\n"
            "/broadcast 内容 - 广播消息给所有用户\n\n"
        )
    else:
        if is_user_vip:
            text += "💎 您是会员，投稿内容将免审核自动发布。\n"
        else:
            text += "您可以投稿，投稿后管理员审核通过即可发布。\n"
            text += "点击【成为会员】联系管理员享受免审核特权。\n"

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# 处理投稿按钮点击，简单回复提示
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("请直接发送您想投稿的文字、图片或视频消息，管理员会审核。")

# 管理员命令：添加VIP
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("用法示例：/addvip 用户ID 或 @用户名")
        return
    target = args[0]
    # 只支持数字ID
    try:
        target_id = int(target)
    except:
        # 可能是@用户名，暂不解析用户名转ID，需要管理员提供ID
        await update.message.reply_text("请使用数字用户ID添加会员。")
        return

    if target_id in data["vip_users"]:
        await update.message.reply_text("该用户已是会员。")
    else:
        data["vip_users"].append(target_id)
        save_data(data)
        await update.message.reply_text(f"成功添加会员：{target_id}")

# 管理员命令：删除VIP
async def delvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("用法示例：/delvip 用户ID 或 @用户名")
        return
    target = args[0]
    try:
        target_id = int(target)
    except:
        await update.message.reply_text("请使用数字用户ID删除会员。")
        return

    if target_id in data["vip_users"]:
        data["vip_users"].remove(target_id)
        save_data(data)
        await update.message.reply_text(f"成功删除会员：{target_id}")
    else:
        await update.message.reply_text("该用户不是会员。")

# 管理员命令：启用会员免审核
async def enablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    data["vip_enabled"] = True
    save_data(data)
    await update.message.reply_text("会员免审核机制已启用。")

# 管理员命令：暂停会员免审核
async def disablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    data["vip_enabled"] = False
    save_data(data)
    await update.message.reply_text("会员免审核机制已暂停。")

# 管理员命令：广播消息
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("请在命令后输入要广播的内容。")
        return

    # 这里只演示广播给VIP用户
    count = 0
    for uid in data["vip_users"]:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📣 广播消息：\n\n{text}")
            count += 1
        except:
            pass
    await update.message.reply_text(f"广播已发送，成功发送给{count}位会员。")

# 存储待审核消息: { message_id: { "user_id":, "content":, "type": } }
pending_messages = {}

# 用户发送消息处理
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    is_user_vip = is_vip(user_id)
    vip_enabled = data.get("vip_enabled", True)

    msg = update.message

    # 1. 普通用户发消息：需要审核
    # 2. VIP会员且会员免审核启用：自动匿名发到频道
    # 3. 管理员发消息忽略处理（不做审核）

    if is_user_admin:
        # 管理员发消息不处理
        return

    if is_user_vip and vip_enabled:
        # 免审核直接转发
        await forward_to_channel_anon(context, msg)
        await msg.reply_text("您的投稿已自动发布，感谢支持会员！", quote=False)
        # bot 回复消息1分钟后自动删除
        sent = await msg.reply_text("感谢您的投稿！", quote=False)
        asyncio.create_task(auto_delete_message(context, sent.chat_id, sent.message_id))
    else:
        # 普通用户或免审核关闭时，需要审核

        # 记录待审核消息
        # 支持文字、图片、视频
        content_type = None
        content = None
        file_id = None

        if msg.text:
            content_type = "text"
            content = msg.text
        elif msg.photo:
            content_type = "photo"
            file_id = msg.photo[-1].file_id
        elif msg.video:
            content_type = "video"
            file_id = msg.video.file_id
        else:
            await msg.reply_text("仅支持文字、图片和视频投稿。")
            return

        # 生成一个审核消息，发给管理员带按钮
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ 通过", callback_data=f"approve_{msg.message_id}"),
                InlineKeyboardButton("❌ 拒绝", callback_data=f"reject_{msg.message_id}"),
            ]
        ])

        # 发送给管理员审核
        if content_type == "text":
            sent = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"新投稿（用户ID: {user_id}）:\n\n{content}",
                reply_markup=keyboard,
            )
        elif content_type == "photo":
            sent = await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=file_id,
                caption=f"新投稿（用户ID: {user_id}）",
                reply_markup=keyboard,
            )
        elif content_type == "video":
            sent = await context.bot.send_video(
                chat_id=ADMIN_ID,
                video=file_id,
                caption=f"新投稿（用户ID: {user_id}）",
                reply_markup=keyboard,
            )
        else:
            await msg.reply_text("投稿格式不支持。")
            return

        # 记录待审核信息，关联管理员消息ID到用户投稿消息ID
        pending_messages[sent.message_id] = {
            "user_id": user_id,
            "content_type": content_type,
            "content": content,
            "file_id": file_id,
            "user_message_id": msg.message_id,
            "chat_id": msg.chat_id,
        }

        await msg.reply_text("您的投稿已提交，等待管理员审核。", quote=False)
        # bot 回复消息1分钟后自动删除
        reply_sent = await msg.reply_text("感谢您的投稿，请耐心等待审核。", quote=False)
        asyncio.create_task(auto_delete_message(context, reply_sent.chat_id, reply_sent.message_id))

# 匿名转发到频道
async def forward_to_channel_anon(context: ContextTypes.DEFAULT_TYPE, message):
    # 匿名转发，隐藏用户信息，只转发内容
    if message.text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=message.text)
    elif message.photo:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id)
    elif message.video:
        await context.bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id)

# 审核按钮回调
async def approve_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("你不是管理员，无权限操作", show_alert=True)
        return

    data_payload = query.data
    action, msg_id_str = data_payload.split("_")
    msg_id = int(msg_id_str)

    if msg_id not in pending_messages:
        await query.answer("此投稿已处理或不存在。", show_alert=True)
        return

    msg_info = pending_messages.pop(msg_id)
    target_user_id = msg_info["user_id"]
    content_type = msg_info["content_type"]
    content = msg_info["content"]
    file_id = msg_info["file_id"]

    if action == "approve":
        # 通过，匿名转发到频道
        if content_type == "text":
            await context.bot.send_message(chat_id=CHANNEL_ID, text=content)
        elif content_type == "photo":
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id)
        elif content_type == "video":
            await context.bot.send_video(chat_id=CHANNEL_ID, video=file_id)

        # 通知投稿者
        try:
            await context.bot.send_message(chat_id=target_user_id, text="您的投稿已通过，已发布！")
        except:
            pass

        await query.edit_message_caption("已通过 ✅") if content_type in ("photo", "video") else await query.edit_message_text("已通过 ✅")

    elif action == "reject":
        # 拒绝，通知投稿者
        try:
            await context.bot.send_message(chat_id=target_user_id, text="您的投稿未通过审核。")
        except:
            pass
        await query.edit_message_caption("已拒绝 ❌") if content_type in ("photo", "video") else await query.edit_message_text("已拒绝 ❌")

    await query.answer()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvip", addvip))
    app.add_handler(CommandHandler("delvip", delvip))
    app.add_handler(CommandHandler("enablevip", enablevip))
    app.add_handler(CommandHandler("disablevip", disablevip))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(button_handler, pattern="^submit$"))
    app.add_handler(CallbackQueryHandler(approve_reject_callback, pattern="^(approve|reject)_"))

    # 监听所有文字、图片、视频消息
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_user_message))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )

if __name__ == "__main__":
    main()
