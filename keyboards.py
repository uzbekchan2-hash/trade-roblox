from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Sotish", callback_data="menu_sell"),
            InlineKeyboardButton(text="🛒 Olish", callback_data="menu_buy"),
        ],
        [
            InlineKeyboardButton(text="👤 Profil", callback_data="menu_profile"),
            InlineKeyboardButton(text="📋 Mening e'lonlarim", callback_data="menu_my_listings"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="menu_about"),
        ]
    ])

def browse_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Sotilayotganlar", callback_data="browse_sell"),
            InlineKeyboardButton(text="🛒 Qidirilayotganlar", callback_data="browse_buy"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
    ])

def sell_or_buy_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Sotaman", callback_data="post_sell"),
            InlineKeyboardButton(text="🛒 Olaman", callback_data="post_buy"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
    ])

def confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_listing"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_listing"),
        ]
    ])

def skip_bio_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="skip_bio")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_listing")]
    ])

def back_to_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_main")]
    ])

def listings_nav(current: int, total: int, listing_id: int, listing_type: str):
    buttons = []
    nav = []
    if current > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"nav_{listing_type}_{current-1}"))
    nav.append(InlineKeyboardButton(text=f"{current+1}/{total}", callback_data="noop"))
    if current < total - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"nav_{listing_type}_{current+1}"))
    buttons.append(nav)
    buttons.append([
        InlineKeyboardButton(text="💬 Murojaat", callback_data=f"contact_{listing_id}"),
    ])
    buttons.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def my_listing_keyboard(listing_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{listing_id}")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_main")]
    ])

def confirm_delete(listing_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"confirm_delete_{listing_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="menu_my_listings"),
        ]
    ])
