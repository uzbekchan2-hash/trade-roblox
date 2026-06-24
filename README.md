[README.md](https://github.com/user-attachments/files/29279120/README.md)
# 🧠 Steal a Brainrot — Trade Bot

Roblox "Steal a Brainrot" o'yini uchun Telegram trade boti.

## ⚙️ O'rnatish

### 1. Bot token olish
1. Telegramda @BotFather ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini bering (masalan: `Brainrot Trade Bot`)
4. Username bering (masalan: `brainrot_trade_bot`)
5. Token oling va `config.py` ga kiriting

### 2. config.py ni to'ldirish
```python
BOT_TOKEN = "BU_YERGA_TOKEN_YOZING"
ADMIN_IDS = [BU_YERGA_OZ_TELEGRAM_ID_INI_YOZ]
```

> O'z Telegram ID'ingni bilish uchun @userinfobot ga /start yuboring

### 3. Python paketlarini o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Botni ishga tushirish
```bash
python bot.py
```

---

## 🎮 Bot imkoniyatlari

| Funksiya | Tavsif |
|---------|--------|
| 💰 Sotish | Brainrot sotish e'loni qo'shish (rasm + nom + bio) |
| 🛒 Olish | Qidiruvchi e'loni qo'shish |
| 👤 Profil | Telegram ID, Roblox nik, statistika |
| 📋 Mening e'lonlarim | O'z e'lonlarini ko'rish va o'chirish |
| 🔍 Bozor | Barchaning e'lonlarini ko'rish, navigatsiya |
| 💬 Murojaat | Sotuvchi bilan bog'lanish tugmasi |

## 🛡 Admin buyruqlari
- `/admin` — statistika paneli
- `/broadcast <matn>` — barcha foydalanuvchilarga xabar yuborish

---

## 📁 Fayl tuzilmasi
```
brainrot_trade_bot/
├── bot.py           # Asosiy fayl
├── config.py        # Token va admin ID
├── database.py      # SQLite baza
├── keyboards.py     # Tugmalar
├── requirements.txt
└── handlers/
    ├── start.py     # /start va ro'yxatdan o'tish
    ├── sell.py      # E'lon qo'shish (sotish/olish)
    ├── buy.py       # E'lonlarni ko'rish
    ├── profile.py   # Profil va mening e'lonlarim
    └── admin.py     # Admin panel
```
