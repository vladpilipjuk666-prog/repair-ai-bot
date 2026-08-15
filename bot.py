import os
import base64
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from openai import AsyncOpenAI
from dotenv import load_dotenv


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Поки що залишаємо назви каналів тут.
# Пізніше підставимо твої реальні @username або ID.
PC_REPAIR_CHANNEL = os.getenv("PC_REPAIR_CHANNEL", "@pc_repair")
WEB_DEV_CHANNEL = os.getenv("WEB_DEV_CHANNEL", "@web_dev")

# Модель AI.
# Її можна буде змінити через змінну середовища.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не знайдено TELEGRAM_BOT_TOKEN")

if not OPENAI_API_KEY:
    raise RuntimeError("Не знайдено OPENAI_API_KEY")


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# =========================================================
# BOT + AI
# =========================================================

bot = Bot(token=TELEGRAM_BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())

ai = AsyncOpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# СТАНИ
# =========================================================

class PostCreation(StatesGroup):
    waiting_for_channel = State()
    waiting_for_content = State()
    waiting_for_edit = State()


# =========================================================
# ТИМЧАСОВЕ ЗБЕРІГАННЯ ПОСТІВ
# =========================================================

user_posts = {}


# =========================================================
# КНОПКИ
# =========================================================

def channel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 PC REPAIR",
                    callback_data="channel_pc",
                ),
                InlineKeyboardButton(
                    text="💻 WEB DEV",
                    callback_data="channel_web",
                ),
            ],
        ]
    )


def post_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опублікувати",
                    callback_data="publish_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Переробити",
                    callback_data="edit_post",
                ),
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="cancel_post",
                ),
            ],
        ]
    )


def edit_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Зробити коротше",
                    callback_data="edit_short",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔥 Зробити більш продаючим",
                    callback_data="edit_sales",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧠 Переписати",
                    callback_data="edit_rewrite",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="edit_back",
                ),
            ],
        ]
    )


# =========================================================
# PROMPT ДЛЯ AI
# =========================================================

def build_prompt(channel: str, user_text: str) -> str:

    if channel == "pc":
        brand = """
Ти пишеш для Telegram-каналу PC REPAIR.

Тематика:
- ремонт ноутбуків і ПК;
- діагностика;
- чистка;
- Windows;
- комплектуючі;
- оптимізація;
- відновлення техніки.
"""

    else:
        brand = """
Ти пишеш для Telegram-каналу WEB DEV.

Тематика:
- створення сайтів;
- веброзробка;
- автоматизація;
- боти;
- програмування;
- IT-рішення для бізнесу.
"""

    return f"""
{brand}

Твоє завдання — перетворити повідомлення клієнта/майстра
на готовий Telegram-пост.

ГОЛОВНЕ:

1. Пост має читатися дуже легко.
2. Людина повинна зрозуміти суть буквально за кілька секунд.
3. Не пиши величезні полотна тексту.
4. Прибирай зайву воду.
5. Використовуй короткі абзаци.
6. Можна використовувати емодзі, але помірно.
7. Не вигадуй фактів, яких немає у вихідному тексті.
8. Не використовуй надмірно рекламний стиль.
9. Текст має звучати природно, ніби його написав реальний майстер.
10. Якщо є проблема → коротко покажи проблему.
11. Якщо є виконана робота → покажи, що саме зробили.
12. Якщо є результат → обов'язково покажи результат.
13. Якщо доречно — додай короткий заклик звернутися.
14. Не використовуй фрази типу "ми найкращі", "професіонали своєї справи"
    без конкретного підтвердження.
15. Не повторюй інформацію.

СТРУКТУРА:

🛠 Короткий заголовок

1–2 речення про проблему.

Що зробили:
• пункт
• пункт
• пункт

✅ Результат:
короткий результат.

📩 Якщо потрібна допомога — напиши нам.

Але структура НЕ повинна бути жорстким шаблоном.
Якщо для конкретного поста якась частина не потрібна — прибери її.

Дуже важливо:
пост повинен бути коротким, красивим і зручним для читання
з телефона.

Ось інформація від користувача:

{user_text}

Поверни ТІЛЬКИ готовий текст поста.
Без пояснень.
"""


# =========================================================
# ГЕНЕРАЦІЯ ТЕКСТУ
# =========================================================

async def generate_post(channel: str, user_text: str) -> str:

    prompt = build_prompt(channel, user_text)

    response = await ai.responses.create(
        model=OPENAI_MODEL,
        instructions=(
            "Ти — AI-контент менеджер Telegram-каналу. "
            "Пиши українською мовою. "
            "Твоя головна мета — ясність, короткість і природність."
        ),
        input=prompt,
        max_output_tokens=1000,
    )

    return response.output_text.strip()


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "Привіт! 👋\n\n"
        "Я допоможу швидко створити готовий пост "
        "для твого Telegram-каналу.\n\n"
        "Можеш надіслати:\n"
        "• текст\n"
        "• фото\n"
        "• фото до/після\n"
        "• опис виконаної роботи\n\n"
        "Спочатку вибери канал:",
        reply_markup=channel_keyboard(),
    )

    await state.set_state(PostCreation.waiting_for_channel)


# =========================================================
# ВИБІР PC REPAIR
# =========================================================

@dp.callback_query(
    PostCreation.waiting_for_channel,
    F.data == "channel_pc",
)
async def select_pc(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    await state.update_data(channel="pc")

    await callback.message.edit_text(
        "🖥 Обрано <b>PC REPAIR</b>.\n\n"
        "Тепер надішли мені опис роботи.\n\n"
        "Наприклад:\n"
        "«Клієнт приніс ноутбук Lenovo, "
        "який сильно грівся. Почистив систему охолодження, "
        "замінив термопасту та зробив оптимізацію.»\n\n"
        "Можеш також одразу прикріпити фото.",
        parse_mode="HTML",
    )

    await state.set_state(PostCreation.waiting_for_content)


# =========================================================
# ВИБІР WEB DEV
# =========================================================

@dp.callback_query(
    PostCreation.waiting_for_channel,
    F.data == "channel_web",
)
async def select_web(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    await state.update_data(channel="web")

    await callback.message.edit_text(
        "💻 Обрано <b>WEB DEV</b>.\n\n"
        "Тепер надішли інформацію про роботу.\n\n"
        "Можеш надіслати текст, фото або все разом.",
        parse_mode="HTML",
    )

    await state.set_state(PostCreation.waiting_for_content)


# =========================================================
# ОТРИМАННЯ ТЕКСТУ
# =========================================================

@dp.message(
    PostCreation.waiting_for_content,
    F.text,
)
async def receive_text(message: Message, state: FSMContext):

    data = await state.get_data()

    channel = data.get("channel")

    user_text = message.text

    await message.answer("✍️ Пишу чернетку...")

    try:

        post = await generate_post(
            channel=channel,
            user_text=user_text,
        )

    except Exception as error:

        logger.exception("Помилка генерації: %s", error)

        await message.answer(
            "❌ Не вдалося створити пост.\n"
            "Перевір API-ключ і спробуй ще раз."
        )

        return

    user_posts[message.from_user.id] = {
        "channel": channel,
        "text": user_text,
        "post": post,
        "photos": [],
    }

    await message.answer(
        "📝 <b>Чернетка:</b>\n\n"
        + post,
        parse_mode="HTML",
        reply_markup=post_keyboard(),
    )


# =========================================================
# ОТРИМАННЯ ФОТО
# =========================================================

@dp.message(
    PostCreation.waiting_for_content,
    F.photo,
)
async def receive_photo(message: Message, state: FSMContext):

    data = await state.get_data()

    channel = data.get("channel")

    photo = message.photo[-1]

    file = await bot.get_file(photo.file_id)

    downloaded = await bot.download_file(file.file_path)

    image_bytes = downloaded.read()

    encoded = base64.b64encode(image_bytes).decode("utf-8")

    user_text = message.caption or "Користувач надіслав фотографію."

    await message.answer(
        "📸 Фото отримав.\n"
        "✨ Аналізую інформацію та готую пост..."
    )

    try:

        response = await ai.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "Проаналізуй фотографію та текст користувача. "
                "Підготуй короткий, природний Telegram-пост "
                "українською мовою. "
                "Не вигадуй того, чого не видно або не сказано."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": build_prompt(channel, user_text),
                        },
                        {
                            "type": "input_image",
                            "image_url": (
                                f"data:image/jpeg;base64,{encoded}"
                            ),
                        },
                    ],
                }
            ],
            max_output_tokens=1000,
        )

        post = response.output_text.strip()

    except Exception as error:

        logger.exception("Помилка аналізу фото: %s", error)

        await message.answer(
            "❌ Не вдалося обробити фотографію."
        )

        return

    user_posts[message.from_user.id] = {
        "channel": channel,
        "text": user_text,
        "post": post,
        "photos": [photo.file_id],
    }

    await message.answer(
        "📝 <b>Чернетка:</b>\n\n"
        + post,
        parse_mode="HTML",
        reply_markup=post_keyboard(),
    )


# =========================================================
# ОПУБЛІКУВАТИ
# =========================================================

@dp.callback_query(F.data == "publish_post")
async def publish_post(callback: CallbackQuery):

    await callback.answer()

    user_id = callback.from_user.id

    post_data = user_posts.get(user_id)

    if not post_data:

        await callback.message.answer(
            "❌ Чернетку не знайдено. Створи новий пост."
        )

        return

    channel = post_data["channel"]
    text = post_data["post"]
    photos = post_data.get("photos", [])

    if channel == "pc":
        target_channel = PC_REPAIR_CHANNEL
    else:
        target_channel = WEB_DEV_CHANNEL

    try:

        if photos:

            await bot.send_photo(
                chat_id=target_channel,
                photo=photos[0],
                caption=text,
            )

        else:

            await bot.send_message(
                chat_id=target_channel,
                text=text,
            )

    except Exception as error:

        logger.exception("Помилка публікації: %s", error)

        await callback.message.answer(
            "❌ Не вдалося опублікувати пост.\n\n"
            "Перевір, чи доданий бот адміністратором "
            "у потрібний канал і чи має право публікувати."
        )

        return

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "✅ Пост успішно опубліковано!"
    )

    user_posts.pop(user_id, None)


# =========================================================
# ПЕРЕРОБКА
# =========================================================

@dp.callback_query(F.data == "edit_post")
async def edit_post(callback: CallbackQuery):

    await callback.answer()

    await callback.message.answer(
        "✏️ Як хочеш змінити пост?",
        reply_markup=edit_keyboard(),
    )


# =========================================================
# КОРОТШЕ
# =========================================================

@dp.callback_query(F.data == "edit_short")
async def edit_short(callback: CallbackQuery):

    await callback.answer()

    await regenerate_post(
        callback,
        "Зроби цей пост значно коротшим. "
        "Залиши тільки найважливішу інформацію."
    )


# =========================================================
# ПРОДАЮЧІШЕ
# =========================================================

@dp.callback_query(F.data == "edit_sales")
async def edit_sales(callback: CallbackQuery):

    await callback.answer()

    await regenerate_post(
        callback,
        "Зроби пост більш цікавим для потенційного клієнта, "
        "але без нав'язливої реклами."
    )


# =========================================================
# ПЕРЕПИСАТИ
# =========================================================

@dp.callback_query(F.data == "edit_rewrite")
async def edit_rewrite(callback: CallbackQuery):

    await callback.answer()

    await regenerate_post(
        callback,
        "Повністю перепиши пост іншими словами. "
        "Збережи факти та зроби текст природним."
    )


# =========================================================
# AI ПЕРЕГЕНЕРАЦІЯ
# =========================================================

async def regenerate_post(
    callback: CallbackQuery,
    instruction: str,
):

    user_id = callback.from_user.id

    post_data = user_posts.get(user_id)

    if not post_data:

        await callback.message.answer(
            "❌ Чернетку не знайдено."
        )

        return

    await callback.message.answer(
        "✨ Переробляю..."
    )

    channel = post_data["channel"]
    original_text = post_data["text"]
    current_post = post_data["post"]

    prompt = f"""
Перероби цей Telegram-пост.

Вихідна інформація:
{original_text}

Поточний пост:
{current_post}

Додаткова інструкція:
{instruction}

Зроби результат коротким, зрозумілим і приємним
для читання з телефона.

Не вигадуй нових фактів.

Поверни тільки готовий текст.
"""

    try:

        response = await ai.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "Ти професійний редактор коротких Telegram-постів."
            ),
            input=prompt,
            max_output_tokens=1000,
        )

        new_post = response.output_text.strip()

    except Exception as error:

        logger.exception("Помилка редагування: %s", error)

        await callback.message.answer(
            "❌ Не вдалося переробити пост."
        )

        return

    user_posts[user_id]["post"] = new_post

    await callback.message.answer(
        "📝 <b>Оновлена чернетка:</b>\n\n"
        + new_post,
        parse_mode="HTML",
        reply_markup=post_keyboard(),
    )


# =========================================================
# СКАСУВАННЯ
# =========================================================

@dp.callback_query(F.data == "cancel_post")
async def cancel_post(callback: CallbackQuery):

    await callback.answer()

    user_posts.pop(callback.from_user.id, None)

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "❌ Чернетку скасовано.\n\n"
        "Можеш створити новий пост через /start."
    )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():

    logger.info("Бот запускається...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
