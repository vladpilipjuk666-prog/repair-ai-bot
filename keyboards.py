from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def channel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 PC REPAIR",
                    callback_data="channel:pc",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 WEB DEV",
                    callback_data="channel:web",
                )
            ],
        ]
    )


def content_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Створити пост",
                    callback_data="content:create",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 ДО / ПІСЛЯ",
                    callback_data="content:before_after",
                )
            ],
        ]
    )


def post_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опублікувати",
                    callback_data="post:publish",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редагувати",
                    callback_data="post:edit",
                ),
                InlineKeyboardButton(
                    text="🔄 Переписати",
                    callback_data="post:rewrite",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✂️ Скоротити",
                    callback_data="post:short",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💼 Професійніше",
                    callback_data="post:professional",
                ),
                InlineKeyboardButton(
                    text="📣 Більш продаюче",
                    callback_data="post:sales",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Робота з фото",
                    callback_data="image:menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="post:cancel",
                )
            ],
        ]
    )


def image_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Покращити фото",
                    callback_data="image:enhance",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Створити AI-зображення",
                    callback_data="image:generate",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 ДО / ПІСЛЯ",
                    callback_data="image:before_after",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="image:back",
                )
            ],
        ]
    )
