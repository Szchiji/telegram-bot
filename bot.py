import os
import json
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 配置区
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377

DATA_FILE = "vip_data.json"

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN:
    raise ValueError("请设置环境变量 BOT_TOKEN")

# 读取或初始化会员数据
def load_data():
    try:import os
import json
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 配置区
CHANNEL_ID = -1001763041158
ADMIN_ID = 7848870377

DATA_FILE = "vip_data.json"
PENDING_FILE = "pending_messages.json"

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
PORT = int(os.getenv("PORT", "8443"))

if not BOT_TOKEN:
    raise ValueError("请设置环境变量 BOT_TOKEN")

# 读取或初始化会员数据
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"vip_users": [], "vip_enabled": True}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 读取或初始化待审核消息
def load_pending():
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_pending(pending):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

data = load_data()
pending_messages = load_pending()

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_vip(user_id):
    return user_id in data.get("vip_users", [])

async def resolve_user_id(context: ContextTypes.DEFAULT_TYPE, input_str: str):
    if input_str.startswith("@"):
        try:
            chat = await context.bot.get_chat(input_str)
            return chat.id
        except Exception:
            return None
    else:
        try:
            return int(input_str)
        except Exception:
            return None

# 自动删除消息
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

# 投稿按钮回复
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("请直接发送您想投稿的文字、图片或视频消息，管理员会审核。")

# 管理员添加会员
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("权限不足，只有管理员可以使用此命令。")
        return

    args = context.args
    if not args:
        await update.message.reply_text("用法示例：/addvip 用户ID 或 /addvip @用户名")
        return

    target_id = await resolve_user_id(context, args[0])
    if not target_id:
        await update.message.reply_text("无法找到该用户，请确认用户ID或用户名正确且机器人有交集。")
        return

    if target_id in data["vip_users"]:
        await update.message.reply_text("该用户已是会员。")
    else:
        data["vip_users"].append(target_id)
        save_data(data)
        await update.message.reply_text(f"成功添加会员：{target_id}")

# 管理员删除会员
async def delvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("权限不足，只有管理员可以使用此命令。")
        return

    args = context.args
    if not args:
        await update.message.reply_text("用法示例：/delvip 用户ID 或 /delvip @用户名")
        return

    target_id = await resolve_user_id(context, args[0])
    if not target_id:
        await update.message.reply_text("无法找到该用户，请确认用户ID或用户名正确且机器人有交集。")
        return

    if target_id in data["vip_users"]:
        data["vip_users"].remove(target_id)
        save_data(data)
        await update.message.reply_text(f"成功删除会员：{target_id}")
    else:
        await update.message.reply_text("该用户不是会员。")

# 启用会员免审核
async def enablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("权限不足，只有管理员可以使用此命令。")
        return

    data["vip_enabled"] = True
    save_data(data)
    await update.message.reply_text("会员免审核机制已启用。")

# 暂停会员免审核
async def disablevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("权限不足，只有管理员可以使用此命令。")
        return

    data["vip_enabled"] = False
    save_data(data)
    await update.message.reply_text("会员免审核机制已暂停。")

# 广播消息
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("权限不足，只有管理员可以使用此命令。")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("请在命令后输入要广播的内容。")
        return

    count = 0
    for uid in data["vip_users"]:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📣 广播消息：\n\n{text}")
            count += 1
        except Exception:
            pass
    await update.message.reply_text(f"广播已发送，成功发送给{count}位会员。")

# 用户消息处理
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = update.effective_user.id

    # 跳过机器人消息和管理员消息
    if msg.from_user.is_bot or is_admin(user_id):
        return

    is_user_vip = is_vip(user_id)
    vip_enabled = data.get("vip_enabled", True)

    if is_user_vip and vip_enabled:
        # 免审核直接发布
        await forward_to_channel_anon(context, msg)
        sent = await msg.reply_text("您的投稿已自动发布，感谢支持会员！")
        asyncio.create_task(auto_delete_message(context, sent.chat_id, sent.message_id))
        return

    # 需要审核投稿
    content_type = None
    content = None
    file_id = None
    caption = None

    if msg.text:
        content_type = "text"
        content = msg.text
    elif msg.photo:
        content_type = "photo"
        file_id = msg.photo[-1].file_id
        caption = msg.caption or ""
    elif msg.video:
        content_type = "video"
        file_id = msg.video.file_id
        caption = msg.caption or ""
    else:
        await msg.reply_text("仅支持文字、图片和视频投稿。")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ 通过", callback_data=f"approve_{msg.message_id}"),
                InlineKeyboardButton("❌ 拒绝", callback_data=f"reject_{msg.message_id}"),
            ]
        ]
    )

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
            caption=f"新投稿（用户ID: {user_id}）\n\n{caption}",
            reply_markup=keyboard,
        )
    elif content_type == "video":
        sent = await context.bot.send_video(
            chat_id=ADMIN_ID,
            video=file_id,
            caption=f"新投稿（用户ID: {user_id}）\n\n{caption}",
            reply_markup=keyboard,
        )

    # 记录待审核消息
    pending_messages[str(sent.message_id)] = {
        "user_id": user_id,
        "content_type": content_type,
        "content": content,
        "file_id": file_id,
        "caption": caption,
    }
    save_pending(pending_messages)

    await msg.reply_text("您的投稿已提交，等待管理员审核。")

# 免审核会员投稿匿名转发
async def forward_to_channel_anon(context: ContextTypes.DEFAULT_TYPE, msg):
    if msg.text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg.text)
    elif msg.photo:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=msg.photo[-1].file_id, caption=msg.caption or "")
    elif msg.video:
        await context.bot.send_video(chat_id=CHANNEL_ID, video=msg.video.file_id, caption=msg.caption or "")

# 审核按钮回调
async def approve_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("你不是管理员，无法审核", show_alert=True)
        return

    data_str = query.data
    action, msg_id_str = data_str.split("_", 1)
    msg_id = msg_id_str.strip()

    if msg_id not in pending_messages:
        await query.answer("该投稿已处理或不存在", show_alert=True)
        return

    info = pending_messages[msg_id]
    target_user_id = info["user_id"]
    content_type = info["content_type"]
    content = info["content"]
    file_id = info["file_id"]
    caption = info["caption"]

    if action == "approve":
        # 发布到频道
        if content_type == "text":
            await context.bot.send_message(chat_id=CHANNEL_ID, text=content)
        elif content_type == "photo":
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption or "")
        elif content_type == "video":
            await context.bot.send_video(chat_id=CHANNEL_ID, video=file_id, caption=caption or "")

        # 编辑管理员那条消息为“已通过”
        try:
            await query.message.edit_text(f"✅ 已通过\n\n原文由用户 {target_user_id} 提交")
        except Exception:
            pass

        await query.answer("已通过并发布")
    elif action == "reject":
        # 编辑管理员那条消息为“已拒绝”
        try:
            await query.message.edit_text(f"❌ 已拒绝\n\n原文由用户 {target_user_id} 提交")
        except Exception:
            pass

        # 通知用户被拒绝
        try:
            await context.bot.send_message(chat_id=target_user_id, text="您的投稿未通过审核，如有疑问请联系管理员。")
        except Exception:
            pass

        await query.answer("已拒绝")

    # 删除待审核记录
    del pending_messages[msg_id]
    save_pending(pending_messages)

# FastAPI及Webhook处理
app = FastAPI()

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.update_queue.put(update)
    return Response(status_code=200)

# 初始化机器人
application = ApplicationBuilder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler, pattern="^submit$"))
application.add_handler(CommandHandler("addvip", addvip))
application.add_handler(CommandHandler("delvip", delvip))
application.add_handler(CommandHandler("enablevip", enablevip))
application.add_handler(CommandHandler("disablevip", disablevip))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(MessageHandler(filters.ALL & ~filters.StatusUpdate.ALL, handle_user_message))
application.add_handler(CallbackQueryHandler(approve_reject_callback, pattern="^(approve|reject)_"))

# 启动监听
if __name__ == "__main__":
    import uvicorn

    RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not RENDER_EXTERNAL_HOSTNAME:
        raise ValueError("请设置 RENDER_EXTERNAL_HOSTNAME 环境变量")

    webhook_url = f"https://{RENDER_EXTERNAL_HOSTNAME}{WEBHOOK_PATH}"

    async def main():
        await application.bot.set_webhook(webhook_url)
        uvicorn.run(app, host="0.0.0.0", port=PORT)

    import asyncio

    asyncio.run(main())
