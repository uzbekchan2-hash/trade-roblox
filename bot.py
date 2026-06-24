import logging
import os
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS  = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
# Render persistent disk /data papkasini ishlatamiz
DATA_DIR = os.environ.get("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "brainrot.db")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username    TEXT DEFAULT '',
                roblox_nick TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                name         TEXT    NOT NULL,
                photo_id     TEXT    NOT NULL,
                bio          TEXT    DEFAULT '',
                type         TEXT    NOT NULL DEFAULT 'sell',
                status       TEXT    NOT NULL DEFAULT 'active',
                created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)

def get_user(tid):
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,)).fetchone()
        return dict(row) if row else None

def save_user(tid, username, nick):
    with db() as c:
        c.execute("""
            INSERT INTO users (telegram_id, username, roblox_nick)
            VALUES (?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, roblox_nick=excluded.roblox_nick
        """, (tid, username or '', nick))

def add_listing(user_id, name, photo_id, bio, ltype):
    with db() as c:
        cur = c.execute(
            "INSERT INTO listings (user_id,name,photo_id,bio,type) VALUES (?,?,?,?,?)",
            (user_id, name, photo_id, bio, ltype)
        )
        return cur.lastrowid

def get_listings(ltype):
    with db() as c:
        rows = c.execute("""
            SELECT l.*, u.username, u.roblox_nick
            FROM listings l JOIN users u ON l.user_id=u.telegram_id
            WHERE l.type=? AND l.status='active'
            ORDER BY l.created_at DESC
        """, (ltype,)).fetchall()
        return [dict(r) for r in rows]

def get_my_listings(uid):
    with db() as c:
        rows = c.execute(
            "SELECT * FROM listings WHERE user_id=? AND status='active' ORDER BY created_at DESC", (uid,)
        ).fetchall()
        return [dict(r) for r in rows]

def del_listing(lid, uid):
    with db() as c:
        c.execute("UPDATE listings SET status='deleted' WHERE id=? AND user_id=?", (lid, uid))

def all_users():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def kb_main():
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("💰 Sotish e'loni", callback_data="post_menu"),
        InlineKeyboardButton("🛒 Bozorni ko'rish", callback_data="market"),
    )
    k.add(
        InlineKeyboardButton("👤 Profil", callback_data="profile"),
        InlineKeyboardButton("📋 Mening e'lonlarim", callback_data="my_listings"),
    )
    return k

def kb_post_type():
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("💰 Sotaman", callback_data="type_sell"),
        InlineKeyboardButton("🛒 Olaman",  callback_data="type_buy"),
    )
    k.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back"))
    return k

def kb_market_type():
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("💰 Sotilayotganlar", callback_data="browse_sell"),
        InlineKeyboardButton("🛒 Qidirilayotganlar", callback_data="browse_buy"),
    )
    k.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back"))
    return k

def kb_skip_cancel():
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_bio"),
        InlineKeyboardButton("❌ Bekor", callback_data="cancel"),
    )
    return k

def kb_confirm():
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm"),
        InlineKeyboardButton("❌ Bekor",      callback_data="cancel"),
    )
    return k

def kb_back():
    k = InlineKeyboardMarkup()
    k.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"))
    return k

def kb_browse(index, total, lid, ltype):
    k = InlineKeyboardMarkup(row_width=3)
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"nav_{ltype}_{index-1}"))
    nav.append(InlineKeyboardButton(f"{index+1}/{total}", callback_data="noop"))
    if index < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"nav_{ltype}_{index+1}"))
    k.row(*nav)
    k.add(InlineKeyboardButton("💬 Sotuvchi bilan bog'lanish", callback_data=f"contact_{lid}"))
    k.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"))
    return k

def kb_my_item(lid):
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("🗑 O'chirish", callback_data=f"del_{lid}"),
        InlineKeyboardButton("🔙 Orqaga",   callback_data="my_listings"),
    )
    return k

def kb_del_confirm(lid):
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"delok_{lid}"),
        InlineKeyboardButton("❌ Yo'q",       callback_data="my_listings"),
    )
    return k

# ─── STATES ───────────────────────────────────────────────────────────────────
class Reg(StatesGroup):
    nick = State()

class Post(StatesGroup):
    photo = State()
    name  = State()
    bio   = State()
    done  = State()

class EditNick(StatesGroup):
    nick = State()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
WELCOME = "🧠 <b>Steal a Brainrot — Trade Bot</b>\n\nSalom, <b>{name}</b>! 👋\n\nBrainrotlaringni sotish yoki olish uchun e'lon qo'shing!"

async def send_main(obj, name, state=None):
    if state:
        await state.finish()
    text = WELCOME.format(name=name)
    if isinstance(obj, CallbackQuery):
        try:
            await obj.message.edit_text(text, reply_markup=kb_main())
        except:
            await obj.message.answer(text, reply_markup=kb_main())
    else:
        await obj.answer(text, reply_markup=kb_main())

async def show_listing_card(obj, listings, index, ltype, edit=False):
    item  = listings[index]
    total = len(listings)
    emoji  = "💰" if ltype == "sell" else "🛒"
    action = "SOTILADI" if ltype == "sell" else "OLINADI"
    caption = (
        f"{emoji} <b>{action}</b>\n\n"
        f"🆔 E'lon ID: <code>#{item['id']}</code>\n"
        f"🧠 <b>Brainrot:</b> {item['name']}\n"
        f"👤 <b>Egasi:</b> @{item['username'] or '—'}\n"
        f"🎮 <b>Roblox:</b> <code>{item['roblox_nick']}</code>\n"
        f"📝 <b>Bio:</b> {item['bio'] or 'Yo\'q'}\n\n"
        f"📊 {index+1}/{total} e'lon"
    )
    kb = kb_browse(index, total, item['id'], ltype)
    msg = obj.message if isinstance(obj, CallbackQuery) else obj
    if edit:
        try:
            await msg.edit_caption(caption=caption, reply_markup=kb)
            return
        except:
            pass
    try:
        await msg.delete()
    except:
        pass
    await msg.answer_photo(photo=item['photo_id'], caption=caption, reply_markup=kb)

# ─── BOT & DP ─────────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp  = Dispatcher(bot, storage=MemoryStorage())

# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(msg: Message, state: FSMContext):
    await state.finish()
    user = get_user(msg.from_user.id)
    if user:
        await send_main(msg, msg.from_user.first_name)
    else:
        await msg.answer(f"👋 Salom, <b>{msg.from_user.first_name}</b>!\n\n🎮 Botdan foydalanish uchun <b>Roblox nikingni</b> yozing:")
        await Reg.nick.set()

@dp.message_handler(state=Reg.nick)
async def reg_nick(msg: Message, state: FSMContext):
    nick = msg.text.strip()
    if not (3 <= len(nick) <= 20):
        await msg.answer("❌ Nik 3–20 belgi bo'lishi kerak!")
        return
    save_user(msg.from_user.id, msg.from_user.username, nick)
    await state.finish()
    await msg.answer(
        f"✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n🎮 Roblox nik: <code>{nick}</code>\n🆔 ID: <code>{msg.from_user.id}</code>",
        reply_markup=kb_main()
    )

# ─── BACK / CANCEL ────────────────────────────────────────────────────────────
@dp.callback_query_handler(lambda c: c.data in ("back", "cancel"), state="*")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await send_main(call, call.from_user.first_name, state)

@dp.callback_query_handler(lambda c: c.data == "noop", state="*")
async def cb_noop(call: CallbackQuery):
    await call.answer()

# ─── POST MENU ────────────────────────────────────────────────────────────────
@dp.callback_query_handler(lambda c: c.data == "post_menu")
async def cb_post_menu(call: CallbackQuery):
    if not get_user(call.from_user.id):
        await call.answer("❌ Avval /start bosing!", show_alert=True); return
    await call.message.edit_text("📢 <b>E'lon turi tanlang:</b>", reply_markup=kb_post_type())

@dp.callback_query_handler(lambda c: c.data in ("type_sell", "type_buy"))
async def cb_post_type(call: CallbackQuery, state: FSMContext):
    ltype = "sell" if call.data == "type_sell" else "buy"
    await state.update_data(ltype=ltype)
    emoji = "💰" if ltype == "sell" else "🛒"
    await call.message.edit_text(f"{emoji} <b>Brainrotingizning rasmini yuboring:</b>")
    await Post.photo.set()

@dp.message_handler(content_types=["photo"], state=Post.photo)
async def post_photo(msg: Message, state: FSMContext):
    await state.update_data(photo_id=msg.photo[-1].file_id)
    await msg.answer("✏️ <b>Brainrot nomini yozing:</b>\n<i>(Masalan: Tralalero Tralala)</i>")
    await Post.name.set()

@dp.message_handler(content_types=["text", "sticker", "document", "video", "audio"], state=Post.photo)
async def post_photo_wrong(msg: Message):
    await msg.answer("❌ Faqat <b>rasm</b> yuboring!")

@dp.message_handler(state=Post.name)
async def post_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    if not (2 <= len(name) <= 50):
        await msg.answer("❌ Nom 2–50 belgi bo'lishi kerak!"); return
    await state.update_data(name=name)
    await msg.answer(
        "📝 <b>Bio yozing</b> (ixtiyoriy):\n<i>Nima evaziga trade qilasiz, shartlar...</i>",
        reply_markup=kb_skip_cancel()
    )
    await Post.bio.set()

@dp.message_handler(state=Post.bio)
async def post_bio(msg: Message, state: FSMContext):
    bio = msg.text.strip()
    if len(bio) > 300:
        await msg.answer("❌ Bio 300 belgidan oshmasin!"); return
    await state.update_data(bio=bio)
    await show_post_preview(msg, state)

@dp.callback_query_handler(lambda c: c.data == "skip_bio", state=Post.bio)
async def skip_bio(call: CallbackQuery, state: FSMContext):
    await state.update_data(bio="")
    try: await call.message.delete()
    except: pass
    await show_post_preview(call.message, state)

async def show_post_preview(msg, state: FSMContext):
    data  = await state.get_data()
    ltype = data.get("ltype", "sell")
    emoji  = "💰" if ltype == "sell" else "🛒"
    action = "SOTILADI" if ltype == "sell" else "OLINADI"
    caption = (
        f"{emoji} <b>{action}</b>\n\n"
        f"🧠 <b>Brainrot:</b> {data['name']}\n"
        f"📝 <b>Bio:</b> {data.get('bio') or 'Yo\'q'}\n\n"
        f"<i>Tasdiqlaysizmi?</i>"
    )
    await Post.done.set()
    await msg.answer_photo(photo=data['photo_id'], caption=caption, reply_markup=kb_confirm())

@dp.callback_query_handler(lambda c: c.data == "confirm", state=Post.done)
async def post_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = get_user(call.from_user.id)
    lid  = add_listing(call.from_user.id, data['name'], data['photo_id'], data.get('bio',''), data['ltype'])
    await state.finish()
    action = "Sotish" if data['ltype'] == "sell" else "Olish"
    await call.message.edit_caption(
        caption=(
            f"✅ <b>E'lon qo'shildi!</b>\n\n"
            f"🆔 E'lon ID: <code>#{lid}</code>\n"
            f"🎮 Roblox: <code>{user['roblox_nick']}</code>\n"
            f"📌 Tur: {action}\n"
            f"🧠 {data['name']}"
        ),
        reply_markup=kb_back()
    )

# ─── MARKET ───────────────────────────────────────────────────────────────────
@dp.callback_query_handler(lambda c: c.data == "market")
async def cb_market(call: CallbackQuery):
    sell = get_listings("sell")
    buy  = get_listings("buy")
    await call.message.edit_text(
        f"🛒 <b>Bozor</b>\n\n"
        f"💰 Sotilayotganlar: <b>{len(sell)}</b> ta\n"
        f"🛒 Qidirilayotganlar: <b>{len(buy)}</b> ta",
        reply_markup=kb_market_type()
    )

@dp.callback_query_handler(lambda c: c.data in ("browse_sell", "browse_buy"))
async def cb_browse(call: CallbackQuery):
    ltype    = "sell" if call.data == "browse_sell" else "buy"
    listings = get_listings(ltype)
    if not listings:
        emoji  = "💰" if ltype == "sell" else "🛒"
        action = "sotilayotgan" if ltype == "sell" else "qidirilayotgan"
        await call.message.edit_text(
            f"{emoji} Hozircha {action} brainrotlar yo'q.\n\nBirinchi bo'ling! 🚀",
            reply_markup=kb_back()
        ); return
    await show_listing_card(call, listings, 0, ltype)

@dp.callback_query_handler(lambda c: c.data.startswith("nav_"))
async def cb_nav(call: CallbackQuery):
    _, ltype, idx = call.data.split("_", 2)
    index    = int(idx)
    listings = get_listings(ltype)
    if not listings or index >= len(listings):
        await call.answer("E'lon topilmadi!", show_alert=True); return
    await show_listing_card(call, listings, index, ltype, edit=True)

@dp.callback_query_handler(lambda c: c.data.startswith("contact_"))
async def cb_contact(call: CallbackQuery):
    lid   = int(call.data.split("_")[1])
    items = get_listings("sell") + get_listings("buy")
    item  = next((i for i in items if i["id"] == lid), None)
    if not item:
        await call.answer("E'lon topilmadi!", show_alert=True); return
    if item["user_id"] == call.from_user.id:
        await call.answer("Bu sizning o'z e'loningiz!", show_alert=True); return
    uname = item["username"]
    text  = (f"@{uname}\n🎮 Roblox: {item['roblox_nick']}") if uname else f"🎮 Roblox: {item['roblox_nick']}"
    await call.answer(text, show_alert=True)

# ─── PROFILE ──────────────────────────────────────────────────────────────────
@dp.callback_query_handler(lambda c: c.data == "profile")
async def cb_profile(call: CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.answer("❌ Avval /start bosing!", show_alert=True); return
    items = get_my_listings(call.from_user.id)
    k = InlineKeyboardMarkup(row_width=1)
    k.add(InlineKeyboardButton("✏️ Roblox nikni o'zgartirish", callback_data="edit_nick"))
    k.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"))
    await call.message.edit_text(
        f"👤 <b>Profil</b>\n\n"
        f"🆔 Telegram ID: <code>{call.from_user.id}</code>\n"
        f"📛 @{call.from_user.username or '—'}\n"
        f"🎮 Roblox: <code>{user['roblox_nick']}</code>\n\n"
        f"📊 Aktiv e'lonlar: <b>{len(items)}</b> ta",
        reply_markup=k
    )

@dp.callback_query_handler(lambda c: c.data == "edit_nick")
async def cb_edit_nick(call: CallbackQuery):
    await call.message.edit_text("✏️ Yangi <b>Roblox nikingni</b> yozing:", reply_markup=kb_back())
    await EditNick.nick.set()

@dp.message_handler(state=EditNick.nick)
async def save_nick(msg: Message, state: FSMContext):
    nick = msg.text.strip()
    if not (3 <= len(nick) <= 20):
        await msg.answer("❌ Nik 3–20 belgi bo'lishi kerak!"); return
    save_user(msg.from_user.id, msg.from_user.username, nick)
    await state.finish()
    await msg.answer(f"✅ Yangilandi: <code>{nick}</code>", reply_markup=kb_back())

# ─── MY LISTINGS ──────────────────────────────────────────────────────────────
@dp.callback_query_handler(lambda c: c.data == "my_listings")
async def cb_my_listings(call: CallbackQuery):
    items = get_my_listings(call.from_user.id)
    if not items:
        await call.message.edit_text("📋 Sizda hali e'lon yo'q.", reply_markup=kb_back()); return
    k    = InlineKeyboardMarkup(row_width=1)
    text = "📋 <b>Mening e'lonlarim:</b>\n\n"
    for item in items:
        emoji  = "💰" if item["type"] == "sell" else "🛒"
        action = "Sotiladi" if item["type"] == "sell" else "Olinadi"
        text  += f"{emoji} <code>#{item['id']}</code> — <b>{item['name']}</b> ({action})\n"
        k.add(InlineKeyboardButton(f"{emoji} #{item['id']} — {item['name']}", callback_data=f"myitem_{item['id']}"))
    k.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"))
    try:
        await call.message.edit_text(text, reply_markup=k)
    except:
        await call.message.answer(text, reply_markup=k)

@dp.callback_query_handler(lambda c: c.data.startswith("myitem_"))
async def cb_my_item(call: CallbackQuery):
    lid   = int(call.data.split("_")[1])
    items = get_my_listings(call.from_user.id)
    item  = next((i for i in items if i["id"] == lid), None)
    if not item:
        await call.answer("Topilmadi!", show_alert=True); return
    emoji  = "💰" if item["type"] == "sell" else "🛒"
    action = "SOTILADI" if item["type"] == "sell" else "OLINADI"
    try: await call.message.delete()
    except: pass
    await call.message.answer_photo(
        photo=item['photo_id'],
        caption=(
            f"{emoji} <b>{action}</b>\n\n"
            f"🆔 E'lon ID: <code>#{item['id']}</code>\n"
            f"🧠 {item['name']}\n"
            f"📝 {item['bio'] or 'Yo\'q'}"
        ),
        reply_markup=kb_my_item(lid)
    )

@dp.callback_query_handler(lambda c: c.data.startswith("del_"))
async def cb_del(call: CallbackQuery):
    lid = int(call.data.split("_")[1])
    try:
        await call.message.edit_caption(
            caption="🗑 Rostdan ham o'chirmoqchimisiz?",
            reply_markup=kb_del_confirm(lid)
        )
    except:
        await call.message.answer("🗑 Rostdan ham o'chirmoqchimisiz?", reply_markup=kb_del_confirm(lid))

@dp.callback_query_handler(lambda c: c.data.startswith("delok_"))
async def cb_delok(call: CallbackQuery):
    lid = int(call.data.split("_")[1])
    del_listing(lid, call.from_user.id)
    try: await call.message.delete()
    except: pass
    await call.message.answer("✅ E'lon o'chirildi!", reply_markup=kb_back())

# ─── ADMIN ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["admin"])
async def cmd_admin(msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    users = all_users()
    sell  = get_listings("sell")
    buy   = get_listings("buy")
    last5 = "\n".join(f"• <code>{u['telegram_id']}</code> @{u['username']} — {u['roblox_nick']}" for u in users[:5])
    await msg.answer(
        f"🛡 <b>Admin panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{len(users)}</b>\n"
        f"💰 Sotish: <b>{len(sell)}</b> | 🛒 Olish: <b>{len(buy)}</b>\n\n"
        f"<b>So'nggi 5:</b>\n{last5}"
    )

@dp.message_handler(commands=["broadcast"])
async def cmd_broadcast(msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    text = msg.text.replace("/broadcast", "", 1).strip()
    if not text:
        await msg.answer("Ishlatish: /broadcast <matn>"); return
    users = all_users()
    ok = 0
    for u in users:
        try:
            await bot.send_message(u["telegram_id"], f"📢 <b>Xabar:</b>\n\n{text}")
            ok += 1
        except:
            pass
    await msg.answer(f"✅ {ok}/{len(users)} foydalanuvchiga yuborildi.")

# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
