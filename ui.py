"""Небольшие UI-хелперы."""

from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Редактирует текущее текстовое сообщение, иначе отправляет новое."""
    message = callback.message

    if message is None:
        return

    if message.text is None:
        await message.answer(
            text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return

    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return

        await message.answer(
            text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
