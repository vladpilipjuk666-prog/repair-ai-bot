import os
import asyncio
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from openai import AsyncOpenAI


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ID каналів.
# Поки можна залишити порожніми.
PC_REPAIR_CHANNEL_ID = os.getenv("PC_REPAIR_CHANNEL_ID")
WEB_DEV_CHANNEL_ID = os.getenv("WEB_DEV_CHANNEL_ID")


if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не знайдено TELEGRAM_BOT_TOKEN")

if not OPENAI_API_KEY:
    raise RuntimeError("Не знайдено OPENAI_API_KEY")


# =========================================================
# ІНІЦІАЛІЗАЦІЯ
# =========================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# ТИМЧАСОВЕ ЗБЕРІГАННЯ ДАНИХ КОРИСТУВАЧІВ
# =========================================================

users = {}


# =========================================================
# КЛАВІАТУРИ
# =========================================================

def channel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 PC REPAIR",
                    callback_data="channel_pc"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 WEB DEV",
                    callback_data="channel_web"
                )
            ],
        ]
    )


def post_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опублікувати",
                    callback_data="publish"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Переробити",
                    callback_data="regenerate"
                ),
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="cancel"
                ),
            ],
        ]
    )


# =========================================================
# СИСТЕМНИЙ ПРОМПТ ДЛЯ AI
# =========================================================

SYSTEM_PROMPT = """
Ти — професійний AI-копірайтер для Telegram-каналу.

Твоє завдання — перетворювати короткий опис користувача
на красивий, сучасний і дуже зрозумілий Telegram-пост.

ГОЛОВНІ ПРАВИЛА:

1. Не пиши довгі тексти.
2. Людина повинна зрозуміти головну думку за кілька секунд.
3. Не використовуй воду.
4. Не повторюй одну думку декілька разів.
5. Текст має виглядати живим, а не шаблонним.
6. Використовуй короткі абзаци.
7. Використовуй емодзі тільки там, де вони реально допомагають.
8. Не став багато емодзі.
9. Не використовуй надмірну кількість хештегів.
10. Тон — спокійний, впевнений, професійний і дружній.
11. Не вигадуй факти, яких немає в описі.
12. Якщо користувач описує ремонт — покажи проблему та результат.
13. Якщо користувач описує розробку сайту — покажи, що було зроблено
    та яку користь це дає.
14. Головне — увага людини та легкість читання.

СТРУКТУРА:

Короткий заголовок.

1–2 короткі речення про проблему або завдання.

Що було зроблено.

Короткий результат.

За можливості — короткий заклик звернутися.

Не пиши слова:
"Звичайно", "Радий допомогти", "Ось ваш пост",
"Як штучний інтелект".

Одразу пиши готовий пост.
"""


# =========================================================
# ГЕНЕРАЦІЯ ПОСТА
# =========================================================

async def generate_post(description: str, channel: str) -> str:

    channel_context = ""

    if channel == "PC REPAIR":
        channel_context = """
Тематика каналу: ремонт комп'ютерів та ноутбуків.
Пиши зрозуміло навіть для людини, яка не розбирається в техніці.
"""

    elif channel == "WEB DEV":
        channel_context = """
Тематика каналу: створення сайтів та веб-розробка.
Пояснюй користь простою мовою, без зайвого технічного жаргону.
"""

    prompt = f"""
{channel_context}

Опис від користувача:

{description}

Створи готовий Telegram-пост.
"""

    response = await ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.8,
    )

    return response.choices[0].message.content.strip()


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    users[message.from_user.id] = {
        "channel": None,
        "description": None,
        "post": None,
        "photo_id": None,
    }

    await message.answer(
        "👋 Привіт!\n\n"
        "Я AI-помічник для створення Telegram-постів.\n\n"
        "Надішли мені коротко, що сталося або що ти зробив.\n\n"
        "Наприклад:\n"
        "«Ремонтував Lenovo, перегрівався процесор, "
        "почистив систему охолодження»"
    )


# =========================================================
# ОТРИМАННЯ ФОТО
# =========================================================

@dp.message(F.photo)
async def photo_handler(message: Message):

    user_id = message.from_user.id

    if user_id not in users:
        users[user_id] = {
            "channel": None,
            "description": None,
            "post": None,
            "photo_id": None,
        }

    # Запам'ятовуємо найбільшу версію фото
    users[user_id]["photo_id"] = message.photo[-1].file_id

    caption = message.caption

    if caption:
        users[user_id]["description"] = caption

    await message.answer(
        "📸 Фото отримав!\n\n"
        "Тепер вибери, для якого каналу створюємо пост:",
        reply_markup=channel_keyboard()
    )


# =========================================================
# ОТРИМАННЯ ТЕКСТУ
# =========================================================

@dp.message(F.text)
async def text_handler(message: Message):

    user_id = message.from_user.id

    if user_id not in users:
        users[user_id] = {
            "channel": None,
            "description": None,
            "post": None,
            "photo_id": None,
        }

    # Не обробляємо команди
    if message.text.startswith("/"):
        return

    users[user_id]["description"] = message.text

    await message.answer(
        "👍 Опис отримав.\n\n"
        "Для якого каналу створюємо пост?",
        reply_markup=channel_keyboard()
    )


# =========================================================
# PC REPAIR
# =========================================================

@dp.callback_query(F.data == "channel_pc")
async def choose_pc_channel(callback: CallbackQuery):

    user_id = callback.from_user.id

    users[user_id]["channel"] = "PC REPAIR"

    await callback.message.edit_text(
        "🖥 Канал: PC REPAIR\n\n"
        "⏳ Створюю короткий пост..."
    )

    try:
        post = await generate_post(
            users[user_id]["description"],
            "PC REPAIR"
        )

        users[user_id]["post"] = post

        photo_id = users[user_id].get("photo_id")

        if photo_id:
            await callback.message.delete()

            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo_id,
                caption=post,
                reply_markup=post_keyboard()
            )
        else:
            await callback.message.edit_text(
                post,
                reply_markup=post_keyboard()
            )

    except Exception as e:

        logging.exception(e)

        await callback.message.edit_text(
            "❌ Не вдалося створити пост.\n\n"
            "Перевір налаштування OpenAI API."
        )

    await callback.answer()


# =========================================================
# WEB DEV
# =========================================================

@dp.callback_query(F.data == "channel_web")
async def choose_web_channel(callback: CallbackQuery):

    user_id = callback.from_user.id

    users[user_id]["channel"] = "WEB DEV"

    await callback.message.edit_text(
        "🌐 Канал: WEB DEV\n\n"
        "⏳ Створюю короткий пост..."
    )

    try:
        post = await generate_post(
            users[user_id]["description"],
            "WEB DEV"
        )

        users[user_id]["post"] = post

        photo_id = users[user_id].get("photo_id")

        if photo_id:
            await callback.message.delete()

            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo_id,
                caption=post,
                reply_markup=post_keyboard()
            )
        else:
            await callback.message.edit_text(
                post,
                reply_markup=post_keyboard()
            )

    except Exception as e:

        logging.exception(e)

        await callback.message.edit_text(
            "❌ Не вдалося створити пост.\n\n"
            "Перевір налаштування OpenAI API."
        )

    await callback.answer()


# =========================================================
# ПЕРЕГЕНЕРАЦІЯ
# =========================================================

@dp.callback_query(F.data == "regenerate")
async def regenerate_handler(callback: CallbackQuery):

    user_id = callback.from_user.id

    data = users.get(user_id)

    if not data or not data.get("description"):
        await callback.answer(
            "Немає даних для перегенерації.",
            show_alert=True
        )
        return

    await callback.answer("Переробляю...")

    try:

        post = await generate_post(
            data["description"],
            data["channel"]
        )

        data["post"] = post

        photo_id = data.get("photo_id")

        if photo_id:

            await callback.message.delete()

            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo_id,
                caption=post,
                reply_markup=post_keyboard()
            )

        else:

            await callback.message.edit_text(
                post,
                reply_markup=post_keyboard()
            )

    except Exception:

        logging.exception("Помилка генерації")

        await callback.message.answer(
            "❌ Не вдалося перегенерувати пост."
        )


# =========================================================
# СКАСУВАННЯ
# =========================================================

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery):

    user_id = callback.from_user.id

    if user_id in users:
        users[user_id]["post"] = None
        users[user_id]["photo_id"] = None

    await callback.message.edit_text(
        "❌ Створення поста скасовано.\n\n"
        "Можеш надіслати новий опис."
    )

    await callback.answer()


# =========================================================
# ПУБЛІКАЦІЯ
# =========================================================

@dp.callback_query(F.data == "publish")
async def publish_handler(callback: CallbackQuery):

    user_id = callback.from_user.id

    data = users.get(user_id)

    if not data or not data.get("post"):
        await callback.answer(
            "Пост не знайдено.",
            show_alert=True
        )
        return

    channel = data.get("channel")
    post = data.get("post")
    photo_id = data.get("photo_id")

    if channel == "PC REPAIR":
        channel_id = PC_REPAIR_CHANNEL_ID

    elif channel == "WEB DEV":
        channel_id = WEB_DEV_CHANNEL_ID

    else:
        channel_id = None

    if not channel_id:

        await callback.answer(
            "Канал ще не налаштований.",
            show_alert=True
        )

        await callback.message.answer(
            "⚠️ Публікація поки не налаштована.\n\n"
            "Пізніше додамо ID каналів у налаштування."
        )

        return

    try:

        if photo_id:

            await bot.send_photo(
                chat_id=channel_id,
                photo=photo_id,
                caption=post
            )

        else:

            await bot.send_message(
                chat_id=channel_id,
                text=post
            )

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

        await callback.message.answer(
            "✅ Пост опубліковано!"
        )

        await callback.answer()

    except Exception as e:

        logging.exception(e)

        await callback.answer(
            "Помилка публікації.",
            show_alert=True
        )


# =========================================================
# /CANCEL
# =========================================================

@dp.message(Command("cancel"))
async def command_cancel(message: Message):

    user_id = message.from_user.id

    users.pop(user_id, None)

    await message.answer(
        "❌ Поточне створення скасовано."
    )


# =========================================================
# ЗАПУСК БОТА
# =========================================================

async def main():

    print("🤖 AI Telegram Bot запущено!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
