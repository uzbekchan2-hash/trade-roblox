import logging
import os
import sqlite3

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
DATA_DIR = os.environ.get("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "brainrot.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            roblox_nick TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            photo_id TEXT NOT NULL,
            bio TEXT DEFAULT '',
            type TEXT NOT NULL DEFAULT 'sell',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")

def get_user(tid):
    with get_db() as c:
        row = c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
        return dict(row) if row else None

def save_user(tid, username, nick):
    with get_db() as c:
        c.execute("""INSERT INTO users (telegram_id, username, roblox_nick) VALUES (?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, roblox_nick=excluded.roblox_nick""",
            (tid, username or '', nick))

def add_listing(user_id, name, photo_id, bio, ltype):
    with get_db() as c:
        cur = c.execute("INSERT INTO listings (user_id,name,photo_id,bio,type) VALUES (?,?,?,?,?)",
            (user_id, name, photo_id, bio, ltype))
        return cur.lastrowid

def get_listings(ltype):
    with get_db() as c:
        rows = c.execute("""SELECT l.*, u.username, u.roblox_nick
            FROM listings l JOIN users u ON l.user_id=u.telegram_id
            WHERE l.type=? AND l.status='active' ORDER BY l.created_at DESC""", (ltype,)).fetchall()
        return [dict(r) for r in rows]

def get_my_listings(uid):
    with get_db() as c:
        rows = c.execute("SELECT * FROM listings WHERE user_id=? AND status='active' ORDER BY created_at DESC", (uid,)).fetchall()
        return [dict(r) for r in rows]

def del_listing(lid, uid):
    with get_db() as c:
        c.execute("UPDATE listings SET status='deleted' WHERE id=? AND user_id=?", (lid, uid))

def all_users():
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]

# ─── STATES ───────────────────────────────────────────────────────────────────
REG_NICK = 0
POST_TYPE, POST_PHOTO, POST_NAME, POST_BIO, POST_CONFIRM = 1, 2, 3, 4, 5
EDIT_NICK = 6

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Sotish e'loni", callback_data="post_menu"),
         InlineKeyboardButton("🛒 Bozorni ko'rish", callback_data="market")],
        [InlineKeyboardButton("👤 Profil", callback_data="profile"),
         InlineKeyboardButton("📋 Mening e'lonlarim", callback_data="my_listings")]
    ])

def kb_post_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Sotaman", callback_data="type_sell"),
         InlineKeyboardButton("🛒 Olaman", callback_data="type_buy")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
    ])

def kb_market_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Sotilayotganlar", callback_data="browse_sell"),
         InlineKeyboardButton("🛒 Qidirilayotganlar", callback_data="browse_buy")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
    ])

def kb_skip_cancel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_bio"),
         InlineKeyboardButton("❌ Bekor", callback_data="cancel")]
    ])

def kb_confirm():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_post"),
         InlineKeyboardButton("❌ Bekor", callback_data="cancel")]
    ])

def kb_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")]])

def kb_browse(index, total, lid, ltype):
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"nav_{ltype}_{index-1}"))
    nav.append(InlineKeyboardButton(f"{index+1}/{total}", callback_data="noop"))
    if index < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"nav_{ltype}_{index+1}"))
    return InlineKeyboardMarkup([
        nav,
        [InlineKeyboardButton("💬 Sotuvchi bilan bog'lanish", callback_data=f"contact_{lid}")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")]
    ])

def kb_my_item(lid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 O'chirish", callback_data=f"del_{lid}"),
         InlineKeyboardButton("🔙 Orqaga", callback_data="my_listings")]
    ])

def kb_del_confirm(lid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"delok_{lid}"),
         InlineKeyboardButton("❌ Yo'q", callback_data="my_listings")]
    ])

# ─── HELPERS ──────────────────────────────────────────────────────────────────
WELCOME = "🧠 <b>Steal a Brainrot — Trade Bot</b>\n\nSalom, <b>{name}</b>! 👋\n\nBrainrotlaringni sotish yoki olish uchun e'lon qo'shing!"

async def show_main(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str):
    text = WELCOME.format(name=name)
    context.user_data.clear()
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(text, reply_markup=kb_main(), parse_mode="HTML")
        except:
            await update.callback_query.message.reply_text(text, reply_markup=kb_main(), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb_main(), parse_mode="HTML")

async def show_listing_card(update: Update, listings, index, ltype, edit=False):
    item = listings[index]
    total = len(listings)
    emoji = "💰" if ltype == "sell" else "🛒"
    action = "SOTILADI" if ltype == "sell" else "OLINADI"
    caption = (
        f"{emoji} <b>{action}</b>\n\n"
        f"🆔 E'lon ID: <code>#{item['id']}</code>\n"
        f"🧠 <b>Brainrot:</b> {item['name']}\n"
        f"👤 <b>Egasi:</b> @{item['username'] or '—'}\n"
        f"🎮 <b>Roblox:</b> <code>{item['roblox_nick']}</code>\n"
        f"📝 <b>Bio:</b> {item['bio'] or 'Yo\\'q'}\n\n"
        f"📊 {index+1}/{total} e'lon"
    )
    kb = kb_browse(index, total, item['id'], ltype)
    msg = update.callback_query.message
    if edit:
        try:
            await msg.edit_caption(caption=caption, reply_markup=kb, parse_mode="HTML")
            return
        except:
            pass
    try:
        await msg.delete()
    except:
        pass
    await msg.reply_photo(photo=item['photo_id'], caption=caption, reply_markup=kb, parse_mode="HTML")

# ─── /start ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = get_user(update.effective_user.id)
    if user:
        await show_main(update, context, update.effective_user.first_name)
        return ConversationHandler.END
    await update.message.reply_text(
        f"👋 Salom, <b>{update.effective_user.first_name}</b>!\n\n🎮 Botdan foydalanish uchun <b>Roblox nikingni</b> yozing:",
        parse_mode="HTML"
    )
    return REG_NICK

async def reg_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nick = update.message.text.strip()
    if not (3 <= len(nick) <= 20):
        await update.message.reply_text("❌ Nik 3–20 belgi bo'lishi kerak!")
        return REG_NICK
    save_user(update.effective_user.id, update.effective_user.username, nick)
    await update.message.reply_text(
        f"✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n🎮 Roblox nik: <code>{nick}</code>",
        reply_markup=kb_main(), parse_mode="HTML"
    )
    return ConversationHandler.END

# ─── BACK / CANCEL ────────────────────────────────────────────────────────────
async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.callback_query.answer()
    await show_main(update, context, update.effective_user.first_name)
    return ConversationHandler.END

async def cb_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ─── POST E'LON ───────────────────────────────────────────────────────────────
async def cb_post_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not get_user(update.effective_user.id):
        await update.callback_query.answer("❌ Avval /start bosing!", show_alert=True)
        return
    await update.callback_query.message.edit_text("📢 <b>E'lon turi tanlang:</b>", reply_markup=kb_post_type(), parse_mode="HTML")
    return POST_TYPE

async def cb_post_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ltype = "sell" if update.callback_query.data == "type_sell" else "buy"
    context.user_data['ltype'] = ltype
    emoji = "💰" if ltype == "sell" else "🛒"
    await update.callback_query.message.edit_text(f"{emoji} <b>Brainrotingizning rasmini yuboring:</b>", parse_mode="HTML")
    return POST_PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['photo_id'] = update.message.photo[-1].file_id
    await update.message.reply_text("✏️ <b>Brainrot nomini yozing:</b>\n<i>(Masalan: Tralalero Tralala)</i>", parse_mode="HTML")
    return POST_NAME

async def post_photo_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Faqat <b>rasm</b> yuboring!", parse_mode="HTML")
    return POST_PHOTO

async def post_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not (2 <= len(name) <= 50):
        await update.message.reply_text("❌ Nom 2–50 belgi bo'lishi kerak!")
        return POST_NAME
    context.user_data['name'] = name
    await update.message.reply_text(
        "📝 <b>Bio yozing</b> (ixtiyoriy):\n<i>Nima evaziga trade qilasiz, shartlar...</i>",
        reply_markup=kb_skip_cancel(), parse_mode="HTML"
    )
    return POST_BIO

async def post_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bio = update.message.text.strip()
    if len(bio) > 300:
        await update.message.reply_text("❌ Bio 300 belgidan oshmasin!")
        return POST_BIO
    context.user_data['bio'] = bio
    await show_preview(update, context)
    return POST_CONFIRM

async def skip_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['bio'] = ""
    try: await update.callback_query.message.delete()
    except: pass
    await show_preview(update, context)
    return POST_CONFIRM

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    ltype = data.get('ltype', 'sell')
    emoji = "💰" if ltype == "sell" else "🛒"
    action = "SOTILADI" if ltype == "sell" else "OLINADI"
    caption = (
        f"{emoji} <b>{action}</b>\n\n"
        f"🧠 <b>Brainrot:</b> {data['name']}\n"
        f"📝 <b>Bio:</b> {data.get('bio') or 'Yo\\'q'}\n\n"
        f"<i>Tasdiqlaysizmi?</i>"
    )
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_photo(photo=data['photo_id'], caption=caption, reply_markup=kb_confirm(), parse_mode="HTML")

async def post_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = context.user_data
    user = get_user(update.effective_user.id)
    lid = add_listing(update.effective_user.id, data['name'], data['photo_id'], data.get('bio', ''), data['ltype'])
    context.user_data.clear()
    action = "Sotish" if data['ltype'] == "sell" else "Olish"
    await update.callback_query.message.edit_caption(
        caption=(
            f"✅ <b>E'lon qo'shildi!</b>\n\n"
            f"🆔 E'lon ID: <code>#{lid}</code>\n"
            f"🎮 Roblox: <code>{user['roblox_nick']}</code>\n"
            f"📌 Tur: {action}\n"
            f"🧠 {data['name']}"
        ),
        reply_markup=kb_back(), parse_mode="HTML"
    )
    return ConversationHandler.END

# ─── MARKET ───────────────────────────────────────────────────────────────────
async def cb_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    sell = get_listings("sell")
    buy = get_listings("buy")
    await update.callback_query.message.edit_text(
        f"🛒 <b>Bozor</b>\n\n💰 Sotilayotganlar: <b>{len(sell)}</b> ta\n🛒 Qidirilayotganlar: <b>{len(buy)}</b> ta",
        reply_markup=kb_market_type(), parse_mode="HTML"
    )

async def cb_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ltype = "sell" if update.callback_query.data == "browse_sell" else "buy"
    listings = get_listings(ltype)
    if not listings:
        emoji = "💰" if ltype == "sell" else "🛒"
        action = "sotilayotgan" if ltype == "sell" else "qidirilayotgan"
        await update.callback_query.message.edit_text(
            f"{emoji} Hozircha {action} brainrotlar yo'q.\n\nBirinchi bo'ling! 🚀",
            reply_markup=kb_back()
        )
        return
    await show_listing_card(update, listings, 0, ltype)

async def cb_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    _, ltype, idx = update.callback_query.data.split("_", 2)
    index = int(idx)
    listings = get_listings(ltype)
    if not listings or index >= len(listings):
        await update.callback_query.answer("E'lon topilmadi!", show_alert=True)
        return
    await show_listing_card(update, listings, index, ltype, edit=True)

async def cb_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lid = int(update.callback_query.data.split("_")[1])
    items = get_listings("sell") + get_listings("buy")
    item = next((i for i in items if i["id"] == lid), None)
    if not item:
        await update.callback_query.answer("E'lon topilmadi!", show_alert=True)
        return
    if item["user_id"] == update.effective_user.id:
        await update.callback_query.answer("Bu sizning o'z e'loningiz!", show_alert=True)
        return
    uname = item["username"]
    text = (f"@{uname}\n🎮 Roblox: {item['roblox_nick']}") if uname else f"🎮 Roblox: {item['roblox_nick']}"
    await update.callback_query.answer(text, show_alert=True)

# ─── PROFILE ──────────────────────────────────────────────────────────────────
async def cb_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user = get_user(update.effective_user.id)
    if not user:
        await update.callback_query.answer("❌ Avval /start bosing!", show_alert=True)
        return
    items = get_my_listings(update.effective_user.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Roblox nikni o'zgartirish", callback_data="edit_nick")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")]
    ])
    await update.callback_query.message.edit_text(
        f"👤 <b>Profil</b>\n\n"
        f"🆔 Telegram ID: <code>{update.effective_user.id}</code>\n"
        f"📛 @{update.effective_user.username or '—'}\n"
        f"🎮 Roblox: <code>{user['roblox_nick']}</code>\n\n"
        f"📊 Aktiv e'lonlar: <b>{len(items)}</b> ta",
        reply_markup=kb, parse_mode="HTML"
    )

async def cb_edit_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text("✏️ Yangi <b>Roblox nikingni</b> yozing:", reply_markup=kb_back(), parse_mode="HTML")
    return EDIT_NICK

async def save_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nick = update.message.text.strip()
    if not (3 <= len(nick) <= 20):
        await update.message.reply_text("❌ Nik 3–20 belgi bo'lishi kerak!")
        return EDIT_NICK
    save_user(update.effective_user.id, update.effective_user.username, nick)
    await update.message.reply_text(f"✅ Yangilandi: <code>{nick}</code>", reply_markup=kb_back(), parse_mode="HTML")
    return ConversationHandler.END

# ─── MY LISTINGS ──────────────────────────────────────────────────────────────
async def cb_my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    items = get_my_listings(update.effective_user.id)
    if not items:
        await update.callback_query.message.edit_text("📋 Sizda hali e'lon yo'q.", reply_markup=kb_back())
        return
    kb_rows = []
    text = "📋 <b>Mening e'lonlarim:</b>\n\n"
    for item in items:
        emoji = "💰" if item["type"] == "sell" else "🛒"
        action = "Sotiladi" if item["type"] == "sell" else "Olinadi"
        text += f"{emoji} <code>#{item['id']}</code> — <b>{item['name']}</b> ({action})\n"
        kb_rows.append([InlineKeyboardButton(f"{emoji} #{item['id']} — {item['name']}", callback_data=f"myitem_{item['id']}")])
    kb_rows.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")])
    try:
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")
    except:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")

async def cb_my_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    lid = int(update.callback_query.data.split("_")[1])
    items = get_my_listings(update.effective_user.id)
    item = next((i for i in items if i["id"] == lid), None)
    if not item:
        await update.callback_query.answer("Topilmadi!", show_alert=True)
        return
    emoji = "💰" if item["type"] == "sell" else "🛒"
    action = "SOTILADI" if item["type"] == "sell" else "OLINADI"
    try: await update.callback_query.message.delete()
    except: pass
    await update.callback_query.message.reply_photo(
        photo=item['photo_id'],
        caption=(f"{emoji} <b>{action}</b>\n\n🆔 E'lon ID: <code>#{item['id']}</code>\n🧠 {item['name']}\n📝 {item['bio'] or 'Yo\\'q'}"),
        reply_markup=kb_my_item(lid), parse_mode="HTML"
    )

async def cb_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    lid = int(update.callback_query.data.split("_")[1])
    try:
        await update.callback_query.message.edit_caption(caption="🗑 Rostdan ham o'chirmoqchimisiz?", reply_markup=kb_del_confirm(lid))
    except:
        await update.callback_query.message.reply_text("🗑 Rostdan ham o'chirmoqchimisiz?", reply_markup=kb_del_confirm(lid))

async def cb_delok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    lid = int(update.callback_query.data.split("_")[1])
    del_listing(lid, update.effective_user.id)
    try: await update.callback_query.message.delete()
    except: pass
    await update.callback_query.message.reply_text("✅ E'lon o'chirildi!", reply_markup=kb_back())

# ─── ADMIN ────────────────────────────────────────────────────────────────────
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    users = all_users()
    sell = get_listings("sell")
    buy = get_listings("buy")
    last5 = "\n".join(f"• <code>{u['telegram_id']}</code> @{u['username']} — {u['roblox_nick']}" for u in users[:5])
    await update.message.reply_text(
        f"🛡 <b>Admin panel</b>\n\n👥 Foydalanuvchilar: <b>{len(users)}</b>\n"
        f"💰 Sotish: <b>{len(sell)}</b> | 🛒 Olish: <b>{len(buy)}</b>\n\n<b>So'nggi 5:</b>\n{last5}",
        parse_mode="HTML"
    )

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    text = update.message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await update.message.reply_text("Ishlatish: /broadcast <matn>")
        return
    users = all_users()
    ok = 0
    for u in users:
        try:
            await context.bot.send_message(u["telegram_id"], f"📢 <b>Xabar:</b>\n\n{text}", parse_mode="HTML")
            ok += 1
        except:
            pass
    await update.message.reply_text(f"✅ {ok}/{len(users)} foydalanuvchiga yuborildi.")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cb_post_menu, pattern="^post_menu$"),
            CallbackQueryHandler(cb_edit_nick, pattern="^edit_nick$"),
        ],
        states={
            REG_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_nick)],
            POST_TYPE: [
                CallbackQueryHandler(cb_post_type, pattern="^type_(sell|buy)$"),
                CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
            ],
            POST_PHOTO: [
                MessageHandler(filters.PHOTO, post_photo),
                MessageHandler(~filters.PHOTO & ~filters.COMMAND, post_photo_wrong),
                CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
            ],
            POST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_name),
                CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
            ],
            POST_BIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_bio),
                CallbackQueryHandler(skip_bio, pattern="^skip_bio$"),
                CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
            ],
            POST_CONFIRM: [
                CallbackQueryHandler(post_confirm, pattern="^confirm_post$"),
                CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
            ],
            EDIT_NICK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_nick),
                CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"),
        ],
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(cb_market, pattern="^market$"))
    app.add_handler(CallbackQueryHandler(cb_browse, pattern="^browse_(sell|buy)$"))
    app.add_handler(CallbackQueryHandler(cb_nav, pattern="^nav_"))
    app.add_handler(CallbackQueryHandler(cb_contact, pattern="^contact_"))
    app.add_handler(CallbackQueryHandler(cb_profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(cb_my_listings, pattern="^my_listings$"))
    app.add_handler(CallbackQueryHandler(cb_my_item, pattern="^myitem_"))
    app.add_handler(CallbackQueryHandler(cb_del, pattern="^del_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_delok, pattern="^delok_"))
    app.add_handler(CallbackQueryHandler(cb_back, pattern="^(back|cancel)$"))
    app.add_handler(CallbackQueryHandler(cb_noop, pattern="^noop$"))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
