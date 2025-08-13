import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import os

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен бота из переменной окружения
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Подключение к базе SQLite
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    gender TEXT,
    city TEXT,
    photo_id TEXT,
    about TEXT
)
""")
conn.commit()

# Состояния для регистрации
class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    photo = State()
    about = State()

# Состояния для фильтра поиска
class SearchFilter(StatesGroup):
    gender = State()
    min_age = State()
    max_age = State()

# Команда /start
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        await message.answer("Ты уже зарегистрирован! Используй /search чтобы искать анкеты или /edit чтобы изменить свою.")
    else:
        await message.answer("Привет! Давай создадим твою анкету. Введи своё имя:")
        await Registration.name.set()

# Создание анкеты
@dp.message_handler(state=Registration.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await Registration.age.set()

@dp.message_handler(state=Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введи возраст числом.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Укажи свой пол (М/Ж):")
    await Registration.gender.set()

@dp.message_handler(state=Registration.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    gender = message.text.lower()
    if gender not in ["м", "ж"]:
        await message.answer("Пол должен быть 'М' или 'Ж'.")
        return
    await state.update_data(gender=gender)
    await message.answer("Из какого ты города?")
    await Registration.city.set()

@dp.message_handler(state=Registration.city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Отправь своё фото:")
    await Registration.photo.set()

@dp.message_handler(content_types=["photo"], state=Registration.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("Расскажи немного о себе:")
    await Registration.about.set()

@dp.message_handler(state=Registration.about)
async def reg_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, name, age, gender, city, photo_id, about)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message.from_user.id, data["name"], data["age"], data["gender"], data["city"], data["photo_id"], data["about"]))
    conn.commit()
    await message.answer("Анкета создана! Используй /search чтобы искать анкеты.")
    await state.finish()

# Редактирование анкеты
@dp.message_handler(commands=["edit"])
async def edit_cmd(message: types.Message):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Ты ещё не создавал анкету! Используй /start.")
        return
    await message.answer("Давай создадим анкету заново. Введи своё имя:")
    await Registration.name.set()

# Поиск анкет
@dp.message_handler(commands=["search"])
async def search_cmd(message: types.Message):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Ты ещё не создавал анкету! Используй /start.")
        return
    await message.answer("Фильтр: кого ищем? (М/Ж или 'все')")
    await SearchFilter.gender.set()

@dp.message_handler(state=SearchFilter.gender)
async def filter_gender(message: types.Message, state: FSMContext):
    gender = message.text.lower()
    if gender not in ["м", "ж", "все"]:
        await message.answer("Введи 'М', 'Ж' или 'все'.")
        return
    await state.update_data(gender=gender)
    await message.answer("Минимальный возраст?")
    await SearchFilter.min_age.set()

@dp.message_handler(state=SearchFilter.min_age)
async def filter_min_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Возраст числом, пожалуйста.")
        return
    await state.update_data(min_age=int(message.text))
    await message.answer("Максимальный возраст?")
    await SearchFilter.max_age.set()

@dp.message_handler(state=SearchFilter.max_age)
async def filter_max_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Возраст числом, пожалуйста.")
        return
    await state.update_data(max_age=int(message.text))
    data = await state.get_data()

    if data["gender"] == "все":
        cursor.execute("SELECT * FROM users WHERE age BETWEEN ? AND ? AND user_id != ?",
                       (data["min_age"], data["max_age"], message.from_user.id))
    else:
        cursor.execute("SELECT * FROM users WHERE gender=? AND age BETWEEN ? AND ? AND user_id != ?",
                       (data["gender"], data["min_age"], data["max_age"], message.from_user.id))
    profiles = cursor.fetchall()
    await state.finish()

    if not profiles:
        await message.answer("Анкет по фильтру не найдено.")
        return

    for p in profiles:
        caption = f"{p[1]}, {p[2]} лет, {p[4]}\n\nО себе: {p[6]}"
        await bot.send_photo(chat_id=message.chat.id, photo=p[5], caption=caption)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
