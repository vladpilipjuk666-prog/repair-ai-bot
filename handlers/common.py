"""Общие команды и главное меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import is_admin
from database import get_recent_reviews, get_stats
from keyboards import (
    back_to_menu_keyboard,
    contacts_keyboard,
    main_menu_keyboard,
)
from texts import (
    contacts_text,
    faq_text,
    help_text,
    main_menu_text,
    prices_text,
    reviews_text,
)
from ui import edit_or_send

router = Router(name="common")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()

    if not message.from_user:
        return

    await message.answer(
        main_menu_text(
            message.from_user.full_name,
            is_admin(message.from_user.id),
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "Оберіть дію:",
        reply_markup=main_menu_keyboard(
            is_admin(message.from_user.id)
        ),
    )


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        help_text(),
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()

    if not message.from_user:
        return

    await message.answer(
        "❌ Поточну дію скасовано.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "Оберіть дію:",
        reply_markup=main_menu_keyboard(
            is_admin(message.from_user.id)
        ),
    )


@router.message(Command("id"))
async def id_command(message: Message) -> None:
    if not message.from_user:
        return

    lines = [
        "🆔 <b>Ваші ID</b>",
        "",
        f"User ID: <code>{message.from_user.id}</code>",
        f"Chat ID: <code>{message.chat.id}</code>",
    ]

    if message.from_user.username:
        lines.append(f"Username: @{message.from_user.username}")

    lines.extend(
        [
            "",
            "User ID потрібен для змінної OWNER_ID "
            "(якщо ви власник бота).",
        ]
    )

    await message.answer("\n".join(lines))


@router.message(Command("prices"))
async def prices_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        prices_text(),
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(Command("contacts"))
async def contacts_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        contacts_text(),
        reply_markup=contacts_keyboard(),
    )


@router.message(Command("faq"))
async def faq_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        faq_text(),
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(Command("reviews"))
async def reviews_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        await _reviews_content(),
        reply_markup=back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:main")
async def menu_main(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()

    if callback.message:
        await edit_or_send(
            callback,
            main_menu_text(
                callback.from_user.full_name,
                is_admin(callback.from_user.id),
            ),
            main_menu_keyboard(is_admin(callback.from_user.id)),
        )


@router.callback_query(F.data == "menu:prices")
async def menu_prices(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()

    await edit_or_send(
        callback,
        prices_text(),
        back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:faq")
async def menu_faq(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()

    await edit_or_send(
        callback,
        faq_text(),
        back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:contacts")
async def menu_contacts(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()

    await edit_or_send(
        callback,
        contacts_text(),
        contacts_keyboard(),
    )


@router.callback_query(F.data == "menu:reviews")
async def menu_reviews(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()

    await edit_or_send(
        callback,
        await _reviews_content(),
        back_to_menu_keyboard(),
    )


async def _reviews_content() -> str:
    stats = await get_stats()
    reviews = await get_recent_reviews(limit=5)
    return reviews_text(
        reviews,
        float(stats.get("avg_rating", 0)),
        int(stats.get("rated", 0)),
    )
