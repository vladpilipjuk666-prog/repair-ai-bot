"""Админ-панель мастера: заявки, статусы, цены, статистика, экспорт."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Message,
)

from config import is_admin
from constants import (
    FINAL_STATUSES,
    STATUS_ACTIONS,
)
from database import (
    count_requests,
    get_all_requests,
    get_events,
    get_recent_reviews,
    get_request,
    get_stats,
    list_requests,
    set_master_comment,
    set_price_offer,
    set_status,
)
from keyboards import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_list_keyboard,
    admin_menu_keyboard,
    admin_price_comment_keyboard,
    admin_request_keyboard,
)
from notifications import (
    send_client_message,
    send_price_offer,
    send_request_photos,
    send_status_notification,
)
from states import AdminFlow
from texts import (
    admin_list_text,
    admin_menu_text,
    admin_request_card,
    request_history_text,
    reviews_text,
    stats_text,
)
from ui import edit_or_send
from utils import (
    device_label,
    format_dt,
    format_money,
    h,
    parse_price,
    price_status_label,
    service_label,
    status_label,
)

logger = logging.getLogger(__name__)
router = Router(name="admin")

PAGE_SIZE = 8


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return bool(event.from_user and is_admin(event.from_user.id))


# Все обработчики этого роутера — только для админов.
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# =========================================================
# ВХОД В ПАНЕЛЬ
# =========================================================

async def show_admin_menu(message: Message) -> None:
    stats = await get_stats()
    await message.answer(
        admin_menu_text(stats),
        reply_markup=admin_menu_keyboard(),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_admin_menu(message)


@router.callback_query(F.data == "admin:menu")
async def admin_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()
    stats = await get_stats()

    await edit_or_send(
        callback,
        admin_menu_text(stats),
        admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer("Скасовано")

    stats = await get_stats()
    await edit_or_send(
        callback,
        admin_menu_text(stats),
        admin_menu_keyboard(),
    )


# =========================================================
# СПИСКИ ЗАЯВОК
# =========================================================

@router.callback_query(F.data.startswith("admin:list:"))
async def admin_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = (callback.data or "").split(":")

    if len(parts) != 4:
        await callback.answer("Помилка.", show_alert=True)
        return

    scope = parts[2]
    if scope not in {"new", "active", "all"}:
        await callback.answer("Невідомий розділ.", show_alert=True)
        return

    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0

    total = await count_requests(scope)
    max_page = max(0, (total - 1) // PAGE_SIZE) if total else 0
    page = min(page, max_page)

    requests = await list_requests(scope, page * PAGE_SIZE, PAGE_SIZE)

    await callback.answer()
    await edit_or_send(
        callback,
        admin_list_text(scope, requests, page, total, PAGE_SIZE),
        admin_list_keyboard(requests, scope, page, total, PAGE_SIZE),
    )


# =========================================================
# КАРТОЧКА ЗАЯВКИ
# =========================================================

@router.callback_query(F.data.startswith("admin:view:"))
async def admin_view(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    request_id = _request_id(callback.data)
    if request_id is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)
    if request is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    await callback.answer()
    await edit_or_send(
        callback,
        admin_request_card(request),
        admin_request_keyboard(request),
    )


@router.callback_query(F.data.startswith("admin:history:"))
async def admin_history(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    request_id = _request_id(callback.data)

    if request_id is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    events = await get_events(request.id, limit=15)
    await callback.answer()

    await edit_or_send(
        callback,
        request_history_text(request, events),
        admin_request_keyboard(request),
    )


@router.callback_query(F.data.startswith("admin:photos:"))
async def admin_photos(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await state.clear()
    request_id = _request_id(callback.data)

    if request_id is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if not request.photos:
        await callback.answer("У цій заявці немає фото.", show_alert=True)
        return

    await callback.answer("Надсилаю фото...")
    delivered = await send_request_photos(
        bot,
        callback.from_user.id,
        request.photos,
    )

    if not delivered and callback.message:
        await callback.message.answer(
            "⚠️ Не вдалося надіслати фото. Спробуйте ще раз пізніше."
        )


# =========================================================
# СМЕНА СТАТУСА
# =========================================================

@router.callback_query(F.data.startswith("admin:status:"))
async def admin_status(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await state.clear()
    parts = (callback.data or "").split(":")

    if len(parts) != 4:
        await callback.answer("Помилка.", show_alert=True)
        return

    try:
        request_id = int(parts[2])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    new_status = parts[3]
    request = await get_request(request_id)

    if request is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if new_status not in STATUS_ACTIONS.get(request.status, ()):
        await callback.answer(
            "Цей перехід недоступний для поточного статусу.",
            show_alert=True,
        )
        return

    updated = await set_status(
        request.id,
        new_status,
        comment=f"Статус змінено майстром: {status_label(new_status)}",
    )

    if updated is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    await callback.answer("Статус оновлено")
    await send_status_notification(bot, updated, new_status)

    await edit_or_send(
        callback,
        admin_request_card(updated),
        admin_request_keyboard(updated),
    )


# =========================================================
# ЦЕНА
# =========================================================

@router.callback_query(F.data.startswith("admin:price:"))
async def admin_price_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    request_id = _request_id(callback.data)
    if request_id is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)
    if request is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if request.status in FINAL_STATUSES:
        await callback.answer(
            "Заявка вже закрита. Ціну можна змінювати лише "
            "для активних заявок.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(AdminFlow.price)
    await state.update_data(admin_request_id=request.id)
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            f"💰 <b>Ціна для заявки {request.number}</b>\n\n"
            "Введіть суму в гривнях цифрами, наприклад: <code>2500</code>.\n\n"
            "Можна вказати <code>0</code>, якщо ремонт безкоштовний "
            "або гарантійний.",
            reply_markup=admin_cancel_keyboard(),
        )


@router.message(AdminFlow.price, F.text)
async def admin_price_value(message: Message, state: FSMContext) -> None:
    value = parse_price(message.text)

    if value is None:
        await message.answer(
            "❌ Не вдалося розпізнати суму.\n\n"
            "Введіть ціле число від 0 до 200000, наприклад: 2500."
        )
        return

    data = await state.get_data()
    request_id = data.get("admin_request_id")

    if not isinstance(request_id, int):
        await state.clear()
        await message.answer("Сесія втрачена. Відкрийте заявку знову.")
        return

    request = await get_request(request_id)
    if request is None:
        await state.clear()
        await message.answer("Заявку не знайдено.")
        return

    await state.update_data(admin_price=value)
    await state.set_state(AdminFlow.price_comment)

    await message.answer(
        f"💰 Сума: <b>{format_money(value)}</b>\n\n"
        "Тепер додайте коментар: що входить у ціну, терміни, "
        "вартість запчастин.\n\n"
        "Або натисніть «Без коментаря».",
        reply_markup=admin_price_comment_keyboard(request.id),
    )


@router.message(AdminFlow.price)
async def admin_price_fallback(message: Message) -> None:
    await message.answer(
        "Введіть суму цифрами, наприклад: 2500.",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(AdminFlow.price_comment, F.text)
async def admin_price_comment(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    text = (message.text or "").strip()

    if len(text) > 600:
        await message.answer(
            "❌ Коментар занадто довгий. Максимум 600 символів."
        )
        return

    data = await state.get_data()
    await _finish_price_offer(
        bot=bot,
        message=message,
        state=state,
        request_id=data.get("admin_request_id"),
        price=data.get("admin_price"),
        comment=text or None,
    )


@router.message(AdminFlow.price_comment)
async def admin_price_comment_fallback(message: Message) -> None:
    await message.answer(
        "Напишіть коментар текстом або натисніть «Без коментаря»."
    )


@router.callback_query(F.data.startswith("admin:price_skip:"))
async def admin_price_skip(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    request_id = data.get("admin_request_id")
    price = data.get("admin_price")

    callback_request_id = _request_id(callback.data)

    if (
        current_state != AdminFlow.price_comment.state
        or not isinstance(request_id, int)
        or not isinstance(price, int)
        or callback_request_id != request_id
    ):
        await callback.answer(
            "Сесія застаріла. Відкрийте заявку знову.",
            show_alert=True,
        )
        return

    await callback.answer()

    if callback.message:
        await _finish_price_offer(
            bot=bot,
            message=callback.message,
            state=state,
            request_id=request_id,
            price=price,
            comment=None,
        )


async def _finish_price_offer(
    *,
    bot: Bot,
    message: Message,
    state: FSMContext,
    request_id: object,
    price: object,
    comment: str | None,
) -> None:
    if not isinstance(request_id, int) or not isinstance(price, int):
        await state.clear()
        await message.answer("Сесія втрачена. Відкрийте заявку знову.")
        return

    request = await get_request(request_id)

    if request is None:
        await state.clear()
        await message.answer("Заявку не знайдено.")
        return

    if request.status in FINAL_STATUSES:
        await state.clear()
        await message.answer(
            "Заявка вже закрита. Ціну не змінено.",
            reply_markup=admin_request_keyboard(request),
        )
        return

    request = await set_price_offer(request_id, price, comment)

    if request is None:
        await state.clear()
        await message.answer("Заявку не знайдено.")
        return

    await state.clear()
    delivered = await send_price_offer(bot, request)

    if delivered:
        text = (
            f"✅ <b>Пропозицію надіслано клієнту</b>\n\n"
            f"Заявка: <b>{request.number}</b>\n"
            f"Ціна: <b>{format_money(price)}</b>"
        )
    else:
        text = (
            f"⚠️ <b>Ціну збережено, але клієнт не отримав повідомлення.</b>\n\n"
            f"Заявка: <b>{request.number}</b>\n"
            f"Ціна: <b>{format_money(price)}</b>\n\n"
            "Можливо, клієнт заблокував бота. Зв'яжіться з ним напряму."
        )

    await message.answer(
        text,
        reply_markup=admin_request_keyboard(request),
    )


# =========================================================
# СООБЩЕНИЕ КЛИЕНТУ
# =========================================================

@router.callback_query(F.data.startswith("admin:message:"))
async def admin_message_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    request_id = _request_id(callback.data)
    if request_id is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)
    if request is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminFlow.message)
    await state.update_data(admin_request_id=request.id)
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            f"💬 <b>Повідомлення клієнту</b>\n\n"
            f"Заявка: <b>{request.number}</b>\n"
            f"Клієнт: {h(request.client_name)}\n\n"
            "Напишіть текст, який отримає клієнт у Telegram.",
            reply_markup=admin_cancel_keyboard(),
        )


@router.message(AdminFlow.message, F.text)
async def admin_message_send(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    text = (message.text or "").strip()

    if not text:
        await message.answer("Напишіть текст повідомлення.")
        return

    if len(text) > 1500:
        await message.answer(
            "❌ Повідомлення занадто довге. Максимум 1500 символів."
        )
        return

    data = await state.get_data()
    request_id = data.get("admin_request_id")

    if not isinstance(request_id, int):
        await state.clear()
        await message.answer("Сесія втрачена.")
        return

    request = await get_request(request_id)
    if request is None:
        await state.clear()
        await message.answer("Заявку не знайдено.")
        return

    delivered = await send_client_message(
        bot,
        request.user_id,
        f"💬 <b>Повідомлення від майстра</b>\n"
        f"Заявка: <b>{request.number}</b>\n\n"
        f"{h(text)}",
    )

    await state.clear()

    if delivered:
        updated = await set_master_comment(request.id, text)
        await message.answer(
            "✅ Повідомлення надіслано клієнту.",
            reply_markup=admin_request_keyboard(updated or request),
        )
    else:
        await message.answer(
            "⚠️ Не вдалося надіслати. Можливо, клієнт заблокував бота.",
            reply_markup=admin_request_keyboard(request),
        )


@router.message(AdminFlow.message)
async def admin_message_fallback(message: Message) -> None:
    await message.answer(
        "Напишіть текст повідомлення або натисніть «Скасувати»."
    )


# =========================================================
# СТАТИСТИКА, ОТЗЫВЫ, ЭКСПОРТ
# =========================================================

@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    stats = await get_stats()
    await message.answer(
        stats_text(stats),
        reply_markup=admin_back_keyboard(),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    stats = await get_stats()
    await callback.answer()
    await edit_or_send(
        callback,
        stats_text(stats),
        admin_back_keyboard(),
    )


@router.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_export(message)


@router.callback_query(F.data == "admin:export")
async def admin_export(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer("Готую CSV...")
    if callback.message:
        await _send_export(callback.message)


async def _send_export(message: Message) -> None:
    requests = await get_all_requests()

    if not requests:
        await message.answer(
            "📤 Поки що немає заявок для експорту.",
            reply_markup=admin_back_keyboard(),
        )
        return

    data = _build_csv(requests)
    filename = f"requests_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"

    await message.answer_document(
        BufferedInputFile(data, filename=filename),
        caption=f"📤 Експорт заявок: {len(requests)} шт.",
        reply_markup=admin_back_keyboard(),
    )


def _csv_safe(value: object) -> str:
    """Не даём Excel/LibreOffice исполнить пользовательский текст как формулу."""
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _build_csv(requests) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")

    writer.writerow(
        [
            "Номер",
            "Створено",
            "Статус",
            "Клієнт",
            "Телефон",
            "Telegram",
            "Техніка",
            "Модель",
            "Проблема",
            "Передача",
            "Адреса",
            "Фото",
            "AI-висновок",
            "AI-ціна від",
            "AI-ціна до",
            "AI-впевненість",
            "Ціна",
            "Статус ціни",
            "Оцінка",
            "Відгук",
            "Коментар майстра",
        ]
    )

    for request in requests:
        writer.writerow(
            [
                request.number,
                format_dt(request.created_at),
                status_label(request.status),
                _csv_safe(request.client_name),
                _csv_safe(request.phone),
                _csv_safe(f"@{request.username}") if request.username else "",
                device_label(request.device_type),
                _csv_safe(request.device_model or ""),
                _csv_safe(request.problem),
                service_label(request.service_method),
                _csv_safe(request.address or ""),
                len(request.photos),
                _csv_safe(request.ai_summary or ""),
                request.ai_price_min if request.ai_price_min is not None else "",
                request.ai_price_max if request.ai_price_max is not None else "",
                _csv_safe(request.ai_confidence or ""),
                request.price if request.price is not None else "",
                price_status_label(request.price_status),
                request.rating or "",
                _csv_safe(request.review or ""),
                _csv_safe(request.master_comment or ""),
            ]
        )

    return ("\ufeff" + output.getvalue()).encode("utf-8")


@router.callback_query(F.data == "admin:reviews")
async def admin_reviews(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    stats = await get_stats()
    reviews = await get_recent_reviews(limit=10)

    await callback.answer()
    await edit_or_send(
        callback,
        reviews_text(
            reviews,
            float(stats.get("avg_rating", 0)),
            int(stats.get("rated", 0)),
        ),
        admin_back_keyboard(),
    )


# =========================================================
# УТИЛИТЫ
# =========================================================

def _request_id(callback_data: str | None) -> int | None:
    if not callback_data:
        return None
    try:
        return int(callback_data.split(":")[-1])
    except ValueError:
        return None
