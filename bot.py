import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message

from config import (
    TELEGRAM_BOT_TOKEN,
    PC_REPAIR_CHANNEL_ID,
    WEB_DEV_CHANNEL_ID,
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

from storage import storage

from keyboards import (
    channel_keyboard,
    content_keyboard,
    post_keyboard,
    image_keyboard,
)

from image_tools import (
    download_telegram_photo,
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

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
)

dp = Dispatcher(
    storage=MemoryStorage(),
)


# =========================================================
# STATES
# =========================================================

class BotStates(StatesGroup):

    waiting_for_description = State()

    waiting_for_custom_edit = State()

    waiting_for_image_instruction = State()

    waiting_for_generation_prompt = State()

    waiting_for_before_photo = State()

    waiting_for_after_photo = State()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id

    storage.reset(user_id)

    await state.clear()

    await message.answer(
        "👋 <b>Привіт!</b>\n\n"
        "Я твій AI-помічник для створення "
        "контенту в Telegram.\n\n"
        "Просто розкажи, що ти зробив — "
        "я перетворю це на короткий "
        "і зрозумілий пост.\n\n"
        "📸 Можеш також додати фотографії.",
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
async def help_handler(
    message: Message,
):

    await message.answer(
        "🧠 <b>Що я вмію:</b>\n\n"
        "📝 Створювати короткі пости\n"
        "📸 Аналізувати фотографії\n"
        "🔄 Створювати «До / Після»\n"
        "✂️ Скорочувати текст\n"
        "✏️ Редагувати текст\n"
        "💼 Робити професійнішим\n"
        "📣 Покращувати подачу для клієнта\n"
        "🎨 Генерувати зображення\n"
        "🪄 Редагувати фотографії\n"
        "📤 Публікувати готові пости",
        parse_mode="HTML",
    )


# =========================================================
# CANCEL
# =========================================================

@dp.message(Command("cancel"))
async def cancel_handler(
    message: Message,
    state: FSMContext,
):

    storage.reset(
        message.from_user.id
    )

    await state.clear()

    await message.answer(
        "❌ Поточна операція скасована.\n\n"
        "Для нового поста натисни /start."
    )


# =========================================================
# PC REPAIR
# =========================================================

@dp.callback_query(
    F.data == "channel:pc"
)
async def choose_pc(
    callback: CallbackQuery,
    state: FSMContext,
):

    user_id = callback.from_user.id

    storage.set_channel(
        user_id,
        "PC REPAIR",
    )

    await state.set_state(
        BotStates.waiting_for_description
    )

    await callback.answer()

    await callback.message.edit_text(
        "🖥 <b>PC REPAIR</b>\n\n"
        "Розкажи, що було з технікою "
        "і що ти зробив.\n\n"
        "Можеш одразу додати фото.",
        parse_mode="HTML",
    )


# =========================================================
# WEB DEV
# =========================================================

@dp.callback_query(
    F.data == "channel:web"
)
async def choose_web(
    callback: CallbackQuery,
    state: FSMContext,
):

    user_id = callback.from_user.id

    storage.set_channel(
        user_id,
        "WEB DEV",
    )

    await state.set_state(
        BotStates.waiting_for_description
    )

    await callback.answer()

    await callback.message.edit_text(
        "🌐 <b>WEB DEV</b>\n\n"
        "Розкажи, що було зроблено "
        "і який отримали результат.\n\n"
        "Можеш додати фотографії.",
        parse_mode="HTML",
    )


# =========================================================
# DESCRIPTION
# =========================================================

@dp.message(
    BotStates.waiting_for_description,
    F.text,
)
async def description_handler(
    message: Message,
):

    storage.set_description(
        message.from_user.id,
        message.text,
    )

    await message.answer(
        "👍 Опис отримав.\n\n"
        "Тепер можеш додати фото "
        "або одразу створити пост.",
        reply_markup=content_keyboard(),
    )


# =========================================================
# PHOTO
# =========================================================

@dp.message(
    BotStates.waiting_for_description,
    F.photo,
)
async def photo_handler(
    message: Message,
):

    user_id = message.from_user.id

    photo_id = message.photo[-1].file_id

    storage.add_photo(
        user_id,
        photo_id,
    )

    if message.caption:

        user = storage.get(user_id)

        if user.description:

            user.description += (
                "\n" + message.caption
            )

        else:

            user.description = message.caption

    user = storage.get(user_id)

    await message.answer(
        f"📸 Фото отримано.\n\n"
        f"Зараз додано фото: "
        f"<b>{len(user.photos)}</b>\n\n"
        "Можеш надіслати ще або "
        "створити пост.",
        parse_mode="HTML",
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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    await callback.answer()

    if not user.description:

        await callback.message.answer(
            "⚠️ Спочатку напиши опис роботи."
        )

        return

    await callback.message.answer(
        "🧠 <b>Аналізую інформацію...</b>\n\n"
        "Перевіряю опис та фотографії.",
        parse_mode="HTML",
    )

    image_descriptions = []

    # -----------------------------------------------------
    # ANALYZE PHOTOS
    # -----------------------------------------------------

    if user.photos:

        try:

            images = []

            for photo_id in user.photos:

                image_bytes = (
                    await download_telegram_photo(
                        bot,
                        photo_id,
                    )
                )

                images.append(
                    (
                        image_bytes,
                        "image/jpeg",
                    )
                )

            image_descriptions = (
                await analyze_images(images)
            )

            storage.set_image_descriptions(
                user_id,
                image_descriptions,
            )

        except Exception as error:

            logger.exception(
                "Помилка аналізу фотографій: %s",
                error,
            )

    # -----------------------------------------------------
    # GENERATE POST
    # -----------------------------------------------------

    try:

        post = await generate_post(
            description=user.description,
            channel=user.channel,
            image_descriptions=image_descriptions,
        )

        storage.set_post(
            user_id,
            post,
        )

    except Exception as error:

        logger.exception(
            "Помилка генерації поста: %s",
            error,
        )

        await callback.message.answer(
            "❌ Не вдалося створити пост.\n\n"
            "Перевір налаштування OpenAI API."
        )

        return

    await send_preview(
        callback.message.chat.id,
        user_id,
    )


# =========================================================
# PREVIEW
# =========================================================

async def send_preview(
    chat_id: int,
    user_id: int,
):

    user = storage.get(user_id)

    text = (
        "📝 <b>Готова чернетка:</b>\n\n"
        f"{user.post}"
    )

    if user.photos:

        await bot.send_photo(
            chat_id=chat_id,
            photo=user.photos[0],
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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    await callback.answer(
        "Переписую..."
    )

    try:

        new_post = await regenerate_post(
            description=user.description,
            channel=user.channel,
            previous_post=user.post,
        )

        storage.set_post(
            user_id,
            new_post,
        )

        await send_preview(
            callback.message.chat.id,
            user_id,
        )

    except Exception as error:

        logger.exception(
            "Rewrite error: %s",
            error,
        )

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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    await callback.answer(
        "Скорочую..."
    )

    try:

        new_post = await edit_post(
            user.post,
            (
                "Зроби текст коротшим. "
                "Залиши тільки найважливішу "
                "інформацію. "
                "Пост має читатися дуже швидко."
            ),
        )

        storage.set_post(
            user_id,
            new_post,
        )

        await send_preview(
            callback.message.chat.id,
            user_id,
        )

    except Exception as error:

        logger.exception(
            "Short error: %s",
            error,
        )

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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    await callback.answer(
        "Покращую стиль..."
    )

    try:

        new_post = await edit_post(
            user.post,
            (
                "Зроби текст більш професійним, "
                "спокійним та впевненим. "
                "Не використовуй складний жаргон "
                "і не додавай зайвої реклами."
            ),
        )

        storage.set_post(
            user_id,
            new_post,
        )

        await send_preview(
            callback.message.chat.id,
            user_id,
        )

    except Exception as error:

        logger.exception(
            "Professional error: %s",
            error,
        )

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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    await callback.answer(
        "Покращую подачу..."
    )

    try:

        new_post = await edit_post(
            user.post,
            (
                "Зроби текст більш цікавим "
                "для потенційного клієнта. "
                "Покажи користь та результат роботи, "
                "але без агресивної реклами."
            ),
        )

        storage.set_post(
            user_id,
            new_post,
        )

        await send_preview(
            callback.message.chat.id,
            user_id,
        )

    except Exception as error:

        logger.exception(
            "Sales error: %s",
            error,
        )

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
        "✏️ Напиши, що потрібно змінити.\n\n"
        "Наприклад:\n\n"
        "«Зроби коротше»\n"
        "«Зроби заголовок цікавішим»\n"
        "«Прибери емодзі»\n"
        "«Додай трохи технічних деталей»"
    )


@dp.message(
    BotStates.waiting_for_custom_edit,
    F.text,
)
async def custom_edit_handler(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id

    user = storage.get(user_id)

    await message.answer(
        "🧠 Редагую..."
    )

    try:

        new_post = await edit_post(
            user.post,
            message.text,
        )

        storage.set_post(
            user_id,
            new_post,
        )

        await state.clear()

        await send_preview(
            message.chat.id,
            user_id,
        )

    except Exception as error:

        logger.exception(
            "Custom edit error: %s",
            error,
        )

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
# IMAGE EDIT START
# =========================================================

@dp.callback_query(
    F.data == "image:enhance"
)
async def image_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    await callback.answer()

    await state.set_state(
        BotStates.waiting_for_image_instruction
    )

    await callback.message.answer(
        "🪄 Надішли фотографію.\n\n"
        "Можеш додати підпис з інструкцією.\n\n"
        "Наприклад:\n"
        "«Зроби фото чистішим та яскравішим, "
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

    instruction = message.caption

    if not instruction:

        instruction = (
            "Покращи якість фотографії. "
            "Зроби її чистішою та приємнішою "
            "для публікації, не змінюючи "
            "основний об'єкт."
        )

    await message.answer(
        "🪄 <b>AI редагує фотографію...</b>",
        parse_mode="HTML",
    )

    try:

        image_bytes = (
            await download_telegram_photo(
                bot,
                message.photo[-1].file_id,
            )
        )

        result = await edit_image(
            image_bytes,
            instruction,
        )

        await message.answer_photo(
            result,
            caption="✨ Готово.",
        )

        await state.clear()

    except Exception as error:

        logger.exception(
            "Image edit error: %s",
            error,
        )

        await message.answer(
            "❌ Не вдалося відредагувати фото."
        )


# =========================================================
# IMAGE GENERATION START
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
        "🎨 Опиши зображення, яке потрібно створити.\n\n"
        "Наприклад:\n\n"
        "«Реалістична стильна фотографія "
        "ремонту ноутбука на робочому столі, "
        "сучасна майстерня, технологічний стиль»."
    )


# =========================================================
# IMAGE GENERATION
# =========================================================

@dp.message(
    BotStates.waiting_for_generation_prompt,
    F.text,
)
async def image_generation_handler(
    message: Message,
    state: FSMContext,
):

    await message.answer(
        "🎨 <b>Генерую зображення...</b>",
        parse_mode="HTML",
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

        logger.exception(
            "Image generation error: %s",
            error,
        )

        await message.answer(
            "❌ Не вдалося створити зображення."
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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    user.photo_mode = "before_after"

    user.before_photo = None

    user.after_photo = None

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

    user_id = message.from_user.id

    storage.set_before_photo(
        user_id,
        message.photo[-1].file_id,
    )

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

    user_id = message.from_user.id

    storage.set_after_photo(
        user_id,
        message.photo[-1].file_id,
    )

    user = storage.get(user_id)

    if not user.before_photo:

        await message.answer(
            "❌ Фото «ДО» не знайдено."
        )

        return

    await message.answer(
        "🧠 <b>Створюю «ДО / ПІСЛЯ»...</b>",
        parse_mode="HTML",
    )

    try:

        before_bytes = (
            await download_telegram_photo(
                bot,
                user.before_photo,
            )
        )

        after_bytes = (
            await download_telegram_photo(
                bot,
                user.after_photo,
            )
        )

        result = await create_before_after(
            before_bytes,
            after_bytes,
        )

        await message.answer_photo(
            result,
            caption=(
                "🔄 <b>ДО / ПІСЛЯ</b>\n\n"
                "Готово."
            ),
            parse_mode="HTML",
        )

        await state.clear()

    except Exception as error:

        logger.exception(
            "Before/after error: %s",
            error,
        )

        await message.answer(
            "❌ Не вдалося створити "
            "зображення «ДО / ПІСЛЯ»."
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

    user_id = callback.from_user.id

    user = storage.get(user_id)

    if not user.post:

        await callback.answer(
            "Пост не знайдено.",
            show_alert=True,
        )

        return

    if user.channel == "PC REPAIR":

        channel_id = PC_REPAIR_CHANNEL_ID

    elif user.channel == "WEB DEV":

        channel_id = WEB_DEV_CHANNEL_ID

    else:

        await callback.answer(
            "Канал не вибрано.",
            show_alert=True,
        )

        return

    if not channel_id:

        await callback.answer(
            "ID каналу не налаштовано.",
            show_alert=True,
        )

        return

    try:

        if user.photos:

            await bot.send_photo(
                chat_id=channel_id,
                photo=user.photos[0],
                caption=user.post,
            )

        else:

            await bot.send_message(
                chat_id=channel_id,
                text=user.post,
            )

        await callback.answer(
            "Опубліковано!"
        )

        await callback.message.answer(
            "✅ <b>Пост успішно опубліковано!</b>",
            parse_mode="HTML",
        )

        storage.reset(user_id)

    except Exception as error:

        logger.exception(
            "Publish error: %s",
            error,
        )

        await callback.answer(
            "Помилка публікації.",
            show_alert=True,
        )

        await callback.message.answer(
            "❌ Не вдалося опублікувати пост.\n\n"
            "Перевір:\n"
            "• чи є бот адміністратором каналу;\n"
            "• чи має право публікувати повідомлення;\n"
            "• чи правильний ID каналу."
        )


# =========================================================
# CANCEL POST
# =========================================================

@dp.callback_query(
    F.data == "post:cancel"
)
async def cancel_post_handler(
    callback: CallbackQuery,
    state: FSMContext,
):

    user_id = callback.from_user.id

    storage.reset(user_id)

    await state.clear()

    await callback.answer()

    await callback.message.answer(
        "❌ Пост скасовано.\n\n"
        "Можеш почати заново через /start."
    )


# =========================================================
# IMAGE BACK
# =========================================================

@dp.callback_query(
    F.data == "image:back"
)
async def image_back_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.answer(
        "⬅️ Повернулися до поста.",
        reply_markup=post_keyboard(),
    )


# =========================================================
# UNKNOWN MESSAGE
# =========================================================

@dp.message()
async def fallback_handler(
    message: Message,
):

    await message.answer(
        "🤔 Я не зовсім зрозумів.\n\n"
        "Натисни /start, щоб почати."
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    logger.info(
        "🤖 Repair AI Bot запускається..."
    )

    await dp.start_polling(bot)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())
