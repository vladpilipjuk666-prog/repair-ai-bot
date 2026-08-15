import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import (
    PC_REPAIR_CHANNEL_ID,
    WEB_DEV_CHANNEL_ID,
    TELEGRAM_BOT_TOKEN,
    validate_config,
)

from ai import (
    analyze_images,
    create_before_after,
    edit_image,
    edit_post,
    generate_image,
    generate_post,
    regenerate_post,
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# =========================================================
# CONFIG
# =========================================================

validate_config()


# =========================================================
# TELEGRAM
# =========================================================

bot = Bot(token=TELEGRAM_BOT_TOKEN)

dp = Dispatcher(
    storage=MemoryStorage()
)


# =========================================================
# USER SESSION
# =========================================================

@dataclass
class UserSession:
    channel: Optional[str] = None

    description: str = ""

    post: str = ""

    photos: list[str] = field(default_factory=list)

    photo_mode: str = "normal"

    before_photo: Optional[str] = None

    after_photo: Optional[str] = None

    generated_image: Optional[bytes] = None


sessions: dict[int, UserSession] = {}


def get_session(user_id: int) -> UserSession:

    if user_id not in sessions:
        sessions[user_id] = UserSession()

    return sessions[user_id]


# =========================================================
# FSM STATES
# =========================================================

class BotStates(StatesGroup):

    waiting_for_description = State()

    waiting_for_custom_edit = State()

    waiting_for_image_instruction = State()

    waiting_for_generation_prompt = State()

    waiting_for_before_photo = State()

    waiting_for_after_photo = State()


# =========================================================
# KEYBOARDS
# =========================================================

def channel_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 PC REPAIR",
                    callback_data="channel:pc",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌐 WEB DEV",
                    callback_data="channel:web",
                ),
            ],
        ]
    )


def content_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Створити пост",
                    callback_data="content:create",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 ДО / ПІСЛЯ",
                    callback_data="content:before_after",
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
                    callback_data="post:publish",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редагувати",
                    callback_data="post:edit",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Переписати",
                    callback_data="post:rewrite",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✂️ Скоротити",
                    callback_data="post:short",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💼 Професійніше",
                    callback_data="post:professional",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📣 Більш продаюче",
                    callback_data="post:sales",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="post:cancel",
                ),
            ],
        ]
    )


def image_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Покращити фото",
                    callback_data="image:enhance",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Створити AI-зображення",
                    callback_data="image:generate",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 ДО / ПІСЛЯ",
                    callback_data="image:before_after",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="image:back",
                ),
            ],
        ]
    )


def after_post_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опублікувати",
                    callback_data="post:publish",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редагувати текст",
                    callback_data="post:edit",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Робота з фото",
                    callback_data="image:menu",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="post:cancel",
                ),
            ],
        ]
    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id

    sessions[user_id] = UserSession()

    await state.clear()

    await message.answer(
        "👋 <b>Привіт!</b>\n\n"
        "Я твій AI-помічник для створення контенту.\n\n"
        "Можеш просто написати мені, що ти зробив.\n\n"
        "<i>Наприклад:</i>\n"
        "«Принесли Lenovo Legion. "
        "Сильно грівся і вимикався. "
        "Почистив систему охолодження, "
        "замінив термопасту, перевірив температури.»\n\n"
        "Також можеш одразу надіслати фотографії.",
        parse_mode="HTML",
    )

    await message.answer(
        "Для якого каналу створюємо контент?",
        reply_markup=channel_keyboard(),
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_handler(message: Message):

    await message.answer(
        "🧠 <b>Що я вмію:</b>\n\n"
        "📝 Створювати короткі Telegram-пости\n"
        "📸 Аналізувати фотографії\n"
        "🔄 Робити «До / Після»\n"
        "✂️ Скорочувати текст\n"
        "✏️ Переписувати текст\n"
        "💼 Робити професійнішим\n"
        "📣 Робити більш продаючим\n"
        "🎨 Генерувати зображення\n"
        "🪄 Редагувати фотографії\n"
        "📤 Публікувати готовий пост",
        parse_mode="HTML",
    )


# =========================================================
# CHANNEL: PC
# =========================================================

@dp.callback_query(F.data == "channel:pc")
async def choose_pc(
    callback: CallbackQuery,
    state: FSMContext,
):

    session = get_session(callback.from_user.id)

    session.channel = "PC REPAIR"

    await state.set_state(
        BotStates.waiting_for_description
    )

    await callback.answer()

    await callback.message.edit_text(
        "🖥 <b>PC REPAIR</b>\n\n"
        "Тепер надішли опис роботи.\n\n"
        "Можеш також додати фото.",
        parse_mode="HTML",
    )


# =========================================================
# CHANNEL: WEB
# =========================================================

@dp.callback_query(F.data == "channel:web")
async def choose_web(
    callback: CallbackQuery,
    state: FSMContext,
):

    session = get_session(callback.from_user.id)

    session.channel = "WEB DEV"

    await state.set_state(
        BotStates.waiting_for_description
    )

    await callback.answer()

    await callback.message.edit_text(
        "🌐 <b>WEB DEV</b>\n\n"
        "Тепер надішли опис роботи.\n\n"
        "Можеш також додати фото.",
        parse_mode="HTML",
    )


# =========================================================
# TEXT INPUT
# =========================================================

@dp.message(
    BotStates.waiting_for_description,
    F.text,
)
async def description_handler(
    message: Message,
    state: FSMContext,
):

    session = get_session(message.from_user.id)

    session.description = message.text

    await message.answer(
        "👍 Інформацію отримав.\n\n"
        "Тепер можеш:\n"
        "• додати фотографії;\n"
        "• або одразу створити пост.",
        reply_markup=content_keyboard(),
    )


# =========================================================
# PHOTO INPUT
# =========================================================

@dp.message(
    BotStates.waiting_for_description,
    F.photo,
)
async def photo_handler(
    message: Message,
    state: FSMContext,
):

    session = get_session(message.from_user.id)

    photo_id = message.photo[-1].file_id

    session.photos.append(photo_id)

    if message.caption:

        if session.description:

            session.description += (
                "\n" + message.caption
            )

        else:

            session.description = message.caption

    await message.answer(
        f"📸 Фото отримано.\n\n"
        f"Зараз у сесії: {len(session.photos)} фото.\n\n"
        "Можеш надіслати ще фотографії "
        "або натиснути «Створити пост».",
        reply_markup=content_keyboard(),
    )


# =========================================================
# CREATE POST
# =========================================================

@dp.callback_query(
    F.data == "content:create"
)
async def create_post_handler(
    callback: CallbackQuery,
):

    session = get_session(callback.from_user.id)

    await callback.answer()

    if not session.description:

        await callback.message.answer(
            "Спочатку надішли опис роботи."
        )

        return

    await callback.message.answer(
        "🧠 Аналізую інформацію...\n\n"
        "Це може зайняти декілька секунд."
    )

    image_descriptions = []

    if session.photos:

        try:

            images_for_analysis = []

            for photo_id in session.photos:

                file = await bot.get_file(
                    photo_id
                )

                downloaded = await bot.download_file(
                    file.file_path
                )

                images_for_analysis.append(
                    (
                        downloaded.read(),
                        "image/jpeg",
                    )
                )

            image_descriptions = await analyze_images(
                images_for_analysis
            )

        except Exception:

            logger.exception(
                "Не вдалося проаналізувати фото"
            )

    try:

        post = await generate_post(
            description=session.description,
            channel=session.channel,
            image_descriptions=image_descriptions,
        )

        session.post = post

    except Exception as error:

        logger.exception(error)

        await callback.message.answer(
            "❌ Помилка AI.\n\n"
            "Перевір OPENAI_API_KEY "
            "та налаштування моделі."
        )

        return

    await send_preview(
        callback.message.chat.id,
        session,
    )


# =========================================================
# SEND PREVIEW
# =========================================================

async def send_preview(
    chat_id: int,
    session: UserSession,
):

    text = (
        "📝 <b>Готова чернетка:</b>\n\n"
        f"{session.post}"
    )

    if session.photos:

        await bot.send_photo(
            chat_id=chat_id,
            photo=session.photos[0],
            caption=text,
            parse_mode="HTML",
            reply_markup=post_keyboard(),
        )

    else:

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=post_keyboard(),
        )


# =========================================================
# REWRITE
# =========================================================

@dp.callback_query(
    F.data == "post:rewrite"
)
async def rewrite_handler(
    callback: CallbackQuery,
):

    session = get_session(callback.from_user.id)

    await callback.answer(
        "Переписую..."
    )

    try:

        session.post = await regenerate_post(
            description=session.description,
            channel=session.channel,
            previous_post=session.post,
        )

        await send_preview(
            callback.message.chat.id,
            session,
        )

    except Exception as error:

        logger.exception(error)

        await callback.message.answer(
            "❌ Не вдалося переписати пост."
        )


# =========================================================
# SHORT
# =========================================================

@dp.callback_query(
    F.data == "post:short"
)
async def short_handler(
    callback: CallbackQuery,
):

    session = get_session(callback.from_user.id)

    await callback.answer(
        "Скорочую..."
    )

    try:

        session.post = await edit_post(
            session.post,
            (
                "Зроби пост значно коротшим. "
                "Залиши тільки найважливішу інформацію. "
                "Людина повинна прочитати його дуже швидко."
            ),
        )

        await send_preview(
            callback.message.chat.id,
            session,
        )

    except Exception as error:

        logger.exception(error)

        await callback.message.answer(
            "❌ Не вдалося скоротити пост."
        )


# =========================================================
# PROFESSIONAL
# =========================================================

@dp.callback_query(
    F.data == "post:professional"
)
async def professional_handler(
    callback: CallbackQuery,
):

    session = get_session(callback.from_user.id)

    await callback.answer(
        "Покращую стиль..."
    )

    try:

        session.post = await edit_post(
            session.post,
            (
                "Зроби текст більш професійним "
                "та впевненим, але залиш його простим "
                "і спокійним. Не додавай зайвої реклами."
            ),
        )

        await send_preview(
            callback.message.chat.id,
            session,
        )

    except Exception as error:

        logger.exception(error)

        await callback.message.answer(
            "❌ Не вдалося змінити стиль."
        )


# =========================================================
# SALES
# =========================================================

@dp.callback_query(
    F.data == "post:sales"
)
async def sales_handler(
    callback: CallbackQuery,
):

    session = get_session(callback.from_user.id)

    await callback.answer(
        "Покращую подачу..."
    )

    try:

        session.post = await edit_post(
            session.post,
            (
                "Зроби текст трохи більш цікавим "
                "для потенційного клієнта. "
                "Покажи цінність роботи, "
                "але без агресивної реклами."
            ),
        )

        await send_preview(
            callback.message.chat.id,
            session,
        )

    except Exception as error:

        logger.exception(error)

        await callback.message.answer(
            "❌ Не вдалося змінити подачу."
        )


# =========================================================
# CUSTOM EDIT
# =========================================================

@dp.callback_query(
    F.data == "post:edit"
)
async def custom_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    await callback.answer()

    await state.set_state(
        BotStates.waiting_for_custom_edit
    )

    await callback.message.answer(
        "✏️ Напиши, що саме потрібно змінити.\n\n"
        "Наприклад:\n"
        "«Зроби ще коротше»\n"
        "«Зроби заголовок цікавішим»\n"
        "«Прибери емодзі»\n"
        "«Додай більше технічних деталей»"
    )


@dp.message(
    BotStates.waiting_for_custom_edit,
    F.text,
)
async def custom_edit_handler(
    message: Message,
    state: FSMContext,
):

    session = get_session(message.from_user.id)

    await message.answer(
        "🧠 Редагую..."
    )

    try:

        session.post = await edit_post(
            session.post,
            message.text,
        )

        await state.clear()

        await send_preview(
            message.chat.id,
            session,
        )

    except Exception as error:

        logger.exception(error)

        await message.answer(
            "❌ Не вдалося відредагувати пост."
        )


# =========================================================
# IMAGE MENU
# =========================================================

@dp.callback_query(
    F.data == "image:menu"
)
async def image_menu(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.answer(
        "🖼 <b>Робота із зображенням</b>\n\n"
        "Що хочеш зробити?",
        parse_mode="HTML",
        reply_markup=image_keyboard(),
    )


# =========================================================
# BEFORE / AFTER START
# =========================================================

@dp.callback_query(
    F.data == "content:before_after"
)
async def before_after_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    session = get_session(callback.from_user.id)

    session.photo_mode = "before_after"

    session.before_photo = None
    session.after_photo = None

    await state.set_state(
        BotStates.waiting_for_before_photo
    )

    await callback.answer()

    await callback.message.answer(
        "🔄 <b>Режим ДО / ПІСЛЯ</b>\n\n"
        "Надішли фотографію <b>ДО</b>.",
        parse_mode="HTML",
    )


# =========================================================
# BEFORE PHOTO
# =========================================================

@dp.message(
    BotStates.waiting_for_before_photo,
    F.photo,
)
async def before_photo_handler(
    message: Message,
    state: FSMContext,
):

    session = get_session(message.from_user.id)

    session.before_photo = message.photo[-1].file_id

    await state.set_state(
        BotStates.waiting_for_after_photo
    )

    await message.answer(
        "✅ Фото «ДО» отримано.\n\n"
        "Тепер надішли фотографію <b>ПІСЛЯ</b>.",
        parse_mode="HTML",
    )


# =========================================================
# AFTER PHOTO
# =========================================================

@dp.message(
    BotStates.waiting_for_after_photo,
    F.photo,
)
async def after_photo_handler(
    message: Message,
    state: FSMContext,
):

    session = get_session(message.from_user.id)

    session.after_photo = message.photo[-1].file_id

    await message.answer(
        "🧠 Створюю красиве порівняння..."
    )

    try:

        before_file = await bot.get_file(
            session.before_photo
        )

        after_file = await bot.get_file(
            session.after_photo
        )

        before_download = await bot.download_file(
            before_file.file_path
        )

        after_download = await bot.download_file(
            after_file.file_path
        )

        result = await create_before_after(
            before_download.read(),
            after_download.read(),
        )

        await message.answer_photo(
            result,
            caption=(
                "🔄 <b>ДО / ПІСЛЯ</b>\n\n"
                "Готово."
            ),
            parse_mode="HTML",
            reply_markup=image_keyboard(),
        )

        await state.clear()

    except Exception as error:

        logger.exception(error)

        await message.answer(
            "❌ Не вдалося створити «До / Після»."
        )


# =========================================================
# IMAGE ENHANCE
# =========================================================

@dp.callback_query(
    F.data == "image:enhance"
)
async def enhance_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    await callback.answer()

    await state.set_state(
        BotStates.waiting_for_image_instruction
    )

    await callback.message.answer(
        "🪄 Надішли фото, яке потрібно відредагувати.\n\n"
        "У підписі можеш написати, що саме зробити.\n\n"
        "Наприклад:\n"
        "«Зроби фото яскравішим і чистішим, "
        "але не змінюй техніку»."
    )


# =========================================================
# IMAGE EDIT
# =========================================================

@dp.message(
    BotStates.waiting_for_image_instruction,
    F.photo,
)
async def image_edit_handler(
    message: Message,
    state: FSMContext,
):

    instruction = message.caption or (
        "Покращи якість фотографії. "
        "Зроби її чистішою та приємнішою "
        "для публікації, не змінюючи основний об'єкт."
    )

    try:

        file = await bot.get_file(
            message.photo[-1].file_id
        )

        downloaded = await bot.download_file(
            file.file_path
        )

        result = await edit_image(
            downloaded.read(),
            instruction,
        )

        await message.answer_photo(
            result,
            caption="✨ Готово.",
        )

        await state.clear()

    except Exception as error:

        logger.exception(error)

        await message.answer(
            "❌ Не вдалося відредагувати фото."
        )


# =========================================================
# IMAGE GENERATION
# =========================================================

@dp.callback_query(
    F.data == "image:generate"
)
async def image_generation_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    await callback.answer()

    await state.set_state(
        BotStates.waiting_for_generation_prompt
    )

    await callback.message.answer(
        "🎨 Опиши, яке зображення потрібно створити.\n\n"
        "Наприклад:\n"
        "«Стильна реалістична обкладинка "
        "для поста про ремонт ноутбука, "
        "темний технологічний стиль»."
    )


@dp.message(
    BotStates.waiting_for_generation_prompt,
    F.text,
)
async def image_generation_handler(
    message: Message,
    state: FSMContext,
):

    await message.answer(
        "🎨 Генерую зображення..."
    )

    try:

        result = await generate_image(
            message.text
        )

        await message.answer_photo(
            result,
            caption="✨ Готово.",
        )

        await state.clear()

    except Exception as error:

        logger.exception(error)

        await message.answer(
            "❌ Не вдалося створити зображення."
        )


# =========================================================
# PUBLISH
# =========================================================

@dp.callback_query(
    F.data == "post:publish"
)
async def publish_handler(
    callback: CallbackQuery,
):

    session = get_session(callback.from_user.id)

    if not session.post:

        await callback.answer(
            "Пост не знайдено.",
            show_alert=True,
        )

        return

    if session.channel == "PC REPAIR":

        channel_id = PC_REPAIR_CHANNEL_ID

    elif session.channel == "WEB DEV":

        channel_id = WEB_DEV_CHANNEL_ID

    else:

        channel_id = None

    if not channel_id:

        await callback.answer(
            "Канал ще не налаштований.",
            show_alert=True,
        )

        await callback.message.answer(
            "⚠️ Спочатку потрібно додати ID каналу "
            "в налаштування Railway."
        )

        return

    try:

        if session.photos:

            await bot.send_photo(
                chat_id=channel_id,
                photo=session.photos[0],
                caption=session.post,
            )

        else:

            await bot.send_message(
                chat_id=channel_id,
                text=session.post,
            )

        await callback.answer(
            "Опубліковано!"
        )

        await callback.message.answer(
            "✅ <b>Пост успішно опубліковано!</b>",
            parse_mode="HTML",
        )

        sessions.pop(
            callback.from_user.id,
            None,
        )

    except Exception as error:

        logger.exception(error)

        await callback.answer(
            "Помилка публікації.",
            show_alert=True,
        )

        await callback.message.answer(
            "❌ Не вдалося опублікувати пост.\n\n"
            "Перевір, чи бот є адміністратором каналу "
            "та має право публікувати повідомлення."
        )


# =========================================================
# CANCEL
# =========================================================

@dp.callback_query(
    F.data == "post:cancel"
)
async def cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
):

    sessions.pop(
        callback.from_user.id,
        None,
    )

    await state.clear()

    await callback.answer()

    await callback.message.answer(
        "❌ Створення поста скасовано.\n\n"
        "Можеш почати заново через /start."
    )


# =========================================================
# IMAGE BACK
# =========================================================

@dp.callback_query(
    F.data == "image:back"
)
async def image_back(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.answer(
        "Повернулися до роботи з постом.",
        reply_markup=post_keyboard(),
    )


# =========================================================
# FALLBACK
# =========================================================

@dp.message()
async def fallback_handler(
    message: Message,
):

    await message.answer(
        "Я не зовсім зрозумів команду 😅\n\n"
        "Натисни /start, щоб почати створення поста."
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    logger.info(
        "🤖 Repair AI Bot запускається..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
