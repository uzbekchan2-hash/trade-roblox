import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import start, sell, buy, profile, admin

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

start.register(dp)
sell.register(dp)
buy.register(dp)
profile.register(dp)
admin.register(dp)

if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
