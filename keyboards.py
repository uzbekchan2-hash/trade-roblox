from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Sotish", callback_data="menu_sell"),
        InlineKeyboardButton("🛒 Olish", callback_data="menu_buy"),
    )
    kb.add(
        InlineKeyboardButton("👤 Profil", callback_data="menu_profile"),
        InlineKeyboardButton("📋 Mening e'lonlarim", callback_data="menu_my_listings"),
    )
    kb.add(InlineKeyboardButton("ℹ️ Bot haqida", callback_data="menu_about"))
    return kb

def browse_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Sotilayotganlar", callback_data="browse_sell"),
        InlineKeyboardButton("🛒 Qidirilayotganlar", callback_data="browse_buy"),
    )
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_main"))
    return kb

def sell_or_buy_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Sotaman", callback_data="post_sell"),
        InlineKeyboardButton("🛒 Olaman", callback_data="post_buy"),
    )
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_main"))
    return kb

def confirm_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_listing"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_listing"),
    )
    return kb

def skip_bio_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_bio"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_listing"))
    return kb

def back_to_main():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main"))
    return kb

def listings_nav(current, total, listing_id, listing_type):
    kb = InlineKeyboardMarkup(row_width=3)
    nav = []
    if current > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"nav_{listing_type}_{current-1}"))
    nav.append(InlineKeyboardButton(f"{current+1}/{total}", callback_data="noop"))
    if current < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"nav_{listing_type}_{current+1}"))
    kb.row(*nav)
    kb.add(InlineKeyboardButton("💬 Murojaat", callback_data=f"contact_{listing_id}"))
    kb.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main"))
    return kb

def my_listing_keyboard(listing_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_{listing_id}"))
    kb.add(InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main"))
    return kb

def confirm_delete(listing_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_delete_{listing_id}"),
        InlineKeyboardButton("❌ Yo'q", callback_data="menu_my_listings"),
    )
    return kb
