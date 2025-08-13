import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/frontend/index.html")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start", "miniapp", "open"])
async def start(msg: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton(
            text="🚀 Открыть мини‑приложение",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )
    await msg.answer(
        "Привет! Жми кнопку, чтобы открыть мини‑приложение знакомств внутри Telegram.",
        reply_markup=kb,
    )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
