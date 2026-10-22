"""Фолбэк для неизвестных сообщений и кнопок. Регистрируется последним."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import is_admin
from keyboards import main_menu_keyboard

router = Router(name="fallback")


@router.message(Command("admin", "stats", "export"))
async def admin_denied(message: Message) -> None:
    await message.answer(
        "⛔ Цей розділ доступний лише майстру.",
    )


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback_denied(callback: CallbackQuery) -> None:
    await callback.answer(
        "⛔ Немає доступу.",
        show_alert=True,
    )


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer(
        "Кнопка застаріла. Відкрийте меню заново.",
        show_alert=True,
    )


@router.message()
async def unknown_message(message: Message) -> None:
    if message.text and message.text.startswith("/"):
        await message.answer(
            "🤔 Невідома команда. Натисніть /start, щоб відкрити меню."
        )
        return

    await message.answer(
        "🤔 Я не зовсім зрозумів.\n\n"
        "Скористайтеся меню нижче або натисніть /start.",
        reply_markup=main_menu_keyboard(
            is_admin(message.from_user.id if message.from_user else None)
        ),
    )
