"""Клиентские сценарии: заявка, мои заявки, цены, отзывы."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from ai import estimate_repair
from config import (
    AI_ENABLED,
    MAX_ACTIVE_REQUESTS,
    MAX_ADDRESS_LENGTH,
    MAX_MODEL_LENGTH,
    MAX_NAME_LENGTH,
    MAX_PHOTOS,
    MAX_PROBLEM_LENGTH,
    MAX_REVIEW_LENGTH,
    is_admin,
)
from constants import (
    ADDRESS_REQUIRED,
    DEVICE_TYPES,
    FINAL_STATUSES,
    PRICE_STATUS_OFFERED,
    SERVICE_METHODS,
    STATUS_ACCEPTED,
    STATUS_CANCELED,
    STATUS_DIAGNOSTICS,
    STATUS_DONE,
    STATUS_NEW,
    STATUS_WAITING_PARTS,
)
from database import (
    count_active_requests,
    create_request,
    get_request,
    get_user_requests,
    set_price_decision,
    set_review,
    set_status,
)
from image_tools import download_telegram_photos
from keyboards import (
    address_keyboard,
    back_to_menu_keyboard,
    cancel_confirm_keyboard,
    confirm_keyboard,
    device_keyboard,
    main_menu_keyboard,
    model_keyboard,
    my_requests_keyboard,
    name_keyboard,
    phone_keyboard,
    photos_keyboard,
    request_detail_keyboard,
    review_followup_keyboard,
    review_text_keyboard,
    service_keyboard,
)
from notifications import (
    notify_admins_canceled,
    notify_admins_new_request,
    notify_admins_price_decision,
    notify_admins_review,
)
from states import RequestForm, ReviewFlow
from texts import (
    ai_estimate_text,
    client_request_card,
    confirm_request_text,
    my_requests_text,
    new_request_client_text,
    review_thanks_text,
)
from ui import edit_or_send
from utils import (
    format_money,
    normalize_phone,
)

logger = logging.getLogger(__name__)
router = Router(name="client")


# =========================================================
# СТАРТ ЗАЯВКИ
# =========================================================

async def begin_request(
    message: Message,
    state: FSMContext,
    user_id: int,
) -> None:
    active = await count_active_requests(user_id)

    if active >= MAX_ACTIVE_REQUESTS:
        await state.clear()
        await message.answer(
            f"⚠️ У вас уже <b>{active}</b> активних заявок.\n\n"
            "Щоб створити нову, дочекайтеся завершення поточних "
            "або перегляньте їх у розділі «Мої заявки».",
            reply_markup=my_requests_keyboard(
                await get_user_requests(user_id, limit=5)
            ),
        )
        return

    await state.clear()
    await state.set_state(RequestForm.device_type)
    await state.update_data(photos=[])

    await message.answer(
        "🛠 <b>Крок 1. Що потрібно відремонтувати?</b>\n\n"
        "Оберіть тип техніки.",
        reply_markup=device_keyboard(),
    )


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    await begin_request(message, state, message.from_user.id)


@router.callback_query(F.data == "menu:new")
async def menu_new(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message:
        await begin_request(callback.message, state, callback.from_user.id)


# =========================================================
# ТИП ТЕХНИКИ
# =========================================================

@router.callback_query(RequestForm.device_type, F.data.startswith("device:"))
async def choose_device(callback: CallbackQuery, state: FSMContext) -> None:
    device_type = (callback.data or "").split(":", 1)[-1]

    if device_type not in DEVICE_TYPES:
        await callback.answer("Невідомий тип техніки.", show_alert=True)
        return

    await state.update_data(device_type=device_type)
    await state.set_state(RequestForm.device_model)
    await callback.answer()

    await edit_or_send(
        callback,
        "🏷 <b>Крок 2. Модель техніки</b>\n\n"
        "Напишіть модель, наприклад: <i>ASUS X515</i>, "
        "<i>HP Pavilion 15</i>, <i>Lenovo IdeaPad</i>.\n\n"
        "Якщо не знаєте — натисніть «Пропустити».",
        model_keyboard(),
    )


# =========================================================
# МОДЕЛЬ
# =========================================================

async def ask_problem(message: Message, state: FSMContext) -> None:
    await state.set_state(RequestForm.problem)
    await message.answer(
        "📝 <b>Крок 3. Опишіть проблему</b>\n\n"
        "Що сталося з технікою? Коли це почалося? "
        "Чи є видимі пошкодження?\n\n"
        "Чим детальніше опишете — тим точніше майстер "
        "зможе оцінити ремонт.\n\n"
        "Наприклад: <i>«Ноутбук не вмикається після залиття чаєм, "
        "індикатор зарядки не горить»</i>.",
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(RequestForm.device_model, F.text)
async def device_model_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if not text:
        await message.answer("Напишіть модель або натисніть «Пропустити».")
        return

    if len(text) > MAX_MODEL_LENGTH:
        await message.answer(
            f"❌ Занадто довга назва. Максимум {MAX_MODEL_LENGTH} символів."
        )
        return

    await state.update_data(device_model=text)
    await ask_problem(message, state)


@router.callback_query(RequestForm.device_model, F.data == "flow:skip_model")
async def device_model_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(device_model=None)
    await callback.answer()

    if callback.message:
        await edit_or_send(
            callback,
            "📝 <b>Крок 3. Опишіть проблему</b>\n\n"
            "Що сталося з технікою? Коли це почалося? "
            "Чи є видимі пошкодження?\n\n"
            "Наприклад: <i>«Ноутбук не вмикається після залиття чаєм»</i>.",
            back_to_menu_keyboard(),
        )
        await state.set_state(RequestForm.problem)


@router.message(RequestForm.device_model)
async def device_model_fallback(message: Message) -> None:
    await message.answer(
        "Будь ласка, напишіть модель текстом або натисніть «Пропустити».",
        reply_markup=model_keyboard(),
    )


# =========================================================
# ПРОБЛЕМА
# =========================================================

@router.message(RequestForm.problem, F.text)
async def problem_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if len(text) < 10:
        await message.answer(
            "Опишіть проблему трохи детальніше — хоча б 10 символів."
        )
        return

    if len(text) > MAX_PROBLEM_LENGTH:
        await message.answer(
            f"❌ Опис занадто довгий. Максимум {MAX_PROBLEM_LENGTH} символів."
        )
        return

    await state.update_data(problem=text)
    await state.set_state(RequestForm.photos)
    await message.answer(
        "📸 <b>Крок 4. Фото техніки</b>\n\n"
        f"Надішліть до {MAX_PHOTOS} фото: загальний вигляд, "
        "пошкодження, екран, роз'єми.\n\n"
        "Фото не обов'язкові. Якщо їх немає — натисніть «Далі».",
        reply_markup=photos_keyboard(0),
    )


@router.message(RequestForm.problem)
async def problem_fallback(message: Message) -> None:
    await message.answer("Опишіть проблему текстом, будь ласка.")


# =========================================================
# ФОТО
# =========================================================

@router.message(RequestForm.photos, F.photo)
async def add_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = list(data.get("photos") or [])

    if len(photos) >= MAX_PHOTOS:
        await message.answer(
            f"Уже додано {MAX_PHOTOS} фото — це максимум.\n"
            "Натисніть «Далі», щоб продовжити.",
            reply_markup=photos_keyboard(len(photos)),
        )
        return

    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)

    await message.answer(
        f"📸 Фото {len(photos)}/{MAX_PHOTOS} додано.\n\n"
        "Надішліть ще або натисніть «Далі».",
        reply_markup=photos_keyboard(len(photos)),
    )


@router.message(RequestForm.photos)
async def photos_fallback(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos = list(data.get("photos") or [])

    await message.answer(
        "Надішліть фото як зображення або натисніть «Далі».",
        reply_markup=photos_keyboard(len(photos)),
    )


@router.callback_query(RequestForm.photos, F.data == "flow:photos_done")
async def photos_done(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await callback.answer("Аналізую..." if AI_ENABLED else "Далі")

    data = await state.get_data()

    # Пока идёт AI-анализ, не принимаем кнопки «Далі» и «способ передачи»:
    # иначе пользователь может проскочить шаг или запустить анализ дважды.
    await state.set_state(RequestForm.processing)
    estimate = None

    if AI_ENABLED:
        if callback.message:
            await edit_or_send(
                callback,
                "🤖 <b>Аналізую опис і фото...</b>\n\n"
                "Зазвичай це займає 5–15 секунд.",
                None,
            )

        images: list[bytes] = []
        photo_ids = list(data.get("photos") or [])[:3]

        if photo_ids:
            images = await download_telegram_photos(bot, photo_ids)

        estimate = await estimate_repair(
            device_type=data.get("device_type", "other"),
            device_model=data.get("device_model"),
            problem=data.get("problem", ""),
            images=images,
        )

        # Пользователь мог нажать /cancel или уйти в меню, пока шёл анализ.
        if await state.get_state() != RequestForm.processing.state:
            return

        if estimate:
            await state.update_data(ai=estimate)

        if callback.message:
            if estimate:
                await edit_or_send(
                    callback,
                    ai_estimate_text(estimate),
                    None,
                )
            else:
                await edit_or_send(
                    callback,
                    "✅ Дякую! Переходимо до наступного кроку.",
                    None,
                )

    await state.set_state(RequestForm.service_method)

    if callback.message:
        await callback.message.answer(
            "🚚 <b>Крок 5. Як вам зручно передати техніку?</b>\n\n"
            "Оберіть варіант — майстер узгодить деталі.",
            reply_markup=service_keyboard(),
        )


# =========================================================
# СПОСІБ ПЕРЕДАЧІ
# =========================================================

async def ask_name(message: Message, state: FSMContext) -> None:
    await state.set_state(RequestForm.name)
    await message.answer(
        "👤 <b>Крок 7. Як до вас звертатися?</b>\n\n"
        "Напишіть ім'я або натисніть кнопку, щоб взяти ім'я з Telegram.",
        reply_markup=name_keyboard(),
    )


@router.callback_query(RequestForm.service_method, F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    method = (callback.data or "").split(":", 1)[-1]

    if method not in SERVICE_METHODS:
        await callback.answer("Невідомий спосіб.", show_alert=True)
        return

    await state.update_data(service_method=method)
    await callback.answer()

    if method in ADDRESS_REQUIRED:
        await state.set_state(RequestForm.address)
        if callback.message:
            await edit_or_send(
                callback,
                "📍 <b>Крок 6. Адреса</b>\n\n"
                "Вкажіть адресу в Києві, куди приїхати "
                "кур'єру або майстру.\n\n"
                "Наприклад: <i>вул. Хрещатик, 10, кв. 5</i>.",
                address_keyboard(),
            )
        return

    if callback.message:
        await callback.message.answer(
            "🚶 Добре, чекаємо вас у майстерні.\n\n"
            "👤 <b>Крок 7. Як до вас звертатися?</b>\n\n"
            "Напишіть ім'я або натисніть кнопку нижче.",
            reply_markup=name_keyboard(),
        )
        await state.set_state(RequestForm.name)


# =========================================================
# АДРЕСА
# =========================================================

@router.message(RequestForm.address, F.text)
async def address_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if len(text) < 5:
        await message.answer("Вкажіть адресу детальніше, будь ласка.")
        return

    if len(text) > MAX_ADDRESS_LENGTH:
        await message.answer(
            f"❌ Адреса занадто довга. Максимум {MAX_ADDRESS_LENGTH} символів."
        )
        return

    await state.update_data(address=text)
    await ask_name(message, state)


@router.callback_query(
    RequestForm.address,
    F.data == "flow:skip_address",
)
async def address_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(address="Уточнимо в чаті")
    await callback.answer()

    if callback.message:
        await edit_or_send(
            callback,
            "👤 <b>Крок 7. Як до вас звертатися?</b>\n\n"
            "Напишіть ім'я або натисніть кнопку, щоб взяти ім'я з Telegram.",
            name_keyboard(),
        )
        await state.set_state(RequestForm.name)


@router.message(RequestForm.address)
async def address_fallback(message: Message) -> None:
    await message.answer(
        "Напишіть адресу текстом або натисніть «Уточнимо в чаті».",
        reply_markup=address_keyboard(),
    )


# =========================================================
# ІМ'Я
# =========================================================

async def ask_phone(message: Message, state: FSMContext) -> None:
    await state.set_state(RequestForm.phone)
    await message.answer(
        "📱 <b>Крок 8. Телефон</b>\n\n"
        "Залиште номер, щоб майстер міг зв'язатися.\n\n"
        "Натисніть кнопку нижче або введіть номер вручну, "
        "наприклад: <i>+380 67 123 45 67</i>.",
        reply_markup=phone_keyboard(),
    )


@router.message(RequestForm.name, F.text)
async def name_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if len(text) < 2:
        await message.answer("Напишіть ім'я, будь ласка.")
        return

    if len(text) > MAX_NAME_LENGTH:
        await message.answer(
            f"❌ Ім'я занадто довге. Максимум {MAX_NAME_LENGTH} символів."
        )
        return

    await state.update_data(client_name=text)
    await ask_phone(message, state)


@router.callback_query(RequestForm.name, F.data == "flow:name_tg")
async def name_from_telegram(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    name = callback.from_user.full_name or "Клієнт"
    await state.update_data(client_name=name)

    if callback.message:
        await edit_or_send(
            callback,
            "📱 <b>Крок 8. Телефон</b>\n\n"
            "Залиште номер, щоб майстер міг зв'язатися.\n\n"
            "Натисніть кнопку нижче або введіть номер вручну.",
            None,
        )
        await callback.message.answer(
            "Натисніть кнопку «Надіслати свій номер» "
            "або введіть номер текстом.",
            reply_markup=phone_keyboard(),
        )
        await state.set_state(RequestForm.phone)


@router.message(RequestForm.name)
async def name_fallback(message: Message) -> None:
    await message.answer(
        "Напишіть ім'я текстом або натисніть кнопку нижче.",
        reply_markup=name_keyboard(),
    )


# =========================================================
# ТЕЛЕФОН
# =========================================================

async def finish_phone(
    message: Message,
    state: FSMContext,
    phone: str,
) -> None:
    await state.update_data(phone=phone)
    await state.set_state(RequestForm.confirm)

    await message.answer(
        "📱 Номер збережено.",
        reply_markup=ReplyKeyboardRemove(),
    )

    data = await state.get_data()

    await message.answer(
        confirm_request_text(data),
        reply_markup=confirm_keyboard(),
    )


@router.message(RequestForm.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact

    if contact is None:
        return

    if contact.user_id and message.from_user and contact.user_id != message.from_user.id:
        await message.answer("Будь ласка, надішліть свій власний номер.")
        return

    phone = normalize_phone(contact.phone_number)

    if not phone:
        await message.answer(
            "Не вдалося розпізнати номер. Введіть його текстом, "
            "наприклад: +380 67 123 45 67."
        )
        return

    await finish_phone(message, state, phone)


@router.message(RequestForm.phone, F.text)
async def phone_text(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text)

    if not phone:
        await message.answer(
            "❌ Невірний формат номера.\n\n"
            "Введіть у форматі +380 67 123 45 67 "
            "або натисніть кнопку нижче."
        )
        return

    await finish_phone(message, state, phone)


@router.message(RequestForm.phone)
async def phone_fallback(message: Message) -> None:
    await message.answer(
        "Надішліть номер кнопкою або введіть його текстом.",
        reply_markup=phone_keyboard(),
    )


# =========================================================
# ПІДТВЕРДЖЕННЯ
# =========================================================

@router.callback_query(RequestForm.confirm, F.data == "flow:confirm")
async def confirm_request(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()

    required = {
        "device_type": data.get("device_type"),
        "problem": data.get("problem"),
        "service_method": data.get("service_method"),
        "client_name": data.get("client_name"),
        "phone": data.get("phone"),
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        await callback.answer(
            "Не всі дані заповнені. Почніть заново.",
            show_alert=True,
        )
        return

    active = await count_active_requests(callback.from_user.id)
    if active >= MAX_ACTIVE_REQUESTS:
        await callback.answer(
            "У вас забагато активних заявок.",
            show_alert=True,
        )
        return

    await callback.answer("Створюю заявку...")

    try:
        request = await create_request(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            client_name=data["client_name"],
            phone=data["phone"],
            device_type=data["device_type"],
            device_model=data.get("device_model"),
            problem=data["problem"],
            service_method=data["service_method"],
            address=data.get("address"),
            photos=list(data.get("photos") or []),
            ai=data.get("ai"),
        )
    except Exception:
        logger.exception("Не удалось создать заявку")
        await callback.message.answer(
            "❌ Не вдалося створити заявку. Спробуйте ще раз "
            "або напишіть майстру."
        )
        return

    await state.clear()

    if callback.message:
        await edit_or_send(
            callback,
            new_request_client_text(request),
            main_menu_keyboard(is_admin(callback.from_user.id)),
        )

    await notify_admins_new_request(bot, request)


@router.callback_query(F.data == "flow:restart")
async def restart_request(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.message:
        await begin_request(callback.message, state, callback.from_user.id)


@router.callback_query(F.data == "flow:cancel")
async def cancel_request(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer("Скасовано")

    if callback.message:
        await callback.message.answer(
            "❌ Заповнення скасовано.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await callback.message.answer(
            "Оберіть дію в меню нижче.",
            reply_markup=main_menu_keyboard(
                is_admin(callback.from_user.id)
            ),
        )


# =========================================================
# МОЇ ЗАЯВКИ
# =========================================================

async def show_my_requests(
    message: Message,
    user_id: int,
) -> None:
    requests = await get_user_requests(user_id, limit=10)

    await message.answer(
        my_requests_text(requests),
        reply_markup=my_requests_keyboard(requests),
    )


@router.message(Command("my"))
async def cmd_my(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user:
        await show_my_requests(message, message.from_user.id)


@router.callback_query(F.data == "menu:my")
async def menu_my(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()

    requests = await get_user_requests(callback.from_user.id, limit=10)

    await edit_or_send(
        callback,
        my_requests_text(requests),
        my_requests_keyboard(requests),
    )


@router.callback_query(F.data == "my:list")
async def my_list(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    requests = await get_user_requests(callback.from_user.id, limit=10)

    await edit_or_send(
        callback,
        my_requests_text(requests),
        my_requests_keyboard(requests),
    )


@router.callback_query(F.data.startswith("my:view:"))
async def my_view(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        request_id = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None or request.user_id != callback.from_user.id:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    await callback.answer()
    await state.clear()
    await edit_or_send(
        callback,
        client_request_card(request),
        request_detail_keyboard(request),
    )


@router.callback_query(F.data.startswith("my:cancel:"))
async def my_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        request_id = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None or request.user_id != callback.from_user.id:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if request.status not in {
        STATUS_NEW,
        STATUS_ACCEPTED,
        STATUS_DIAGNOSTICS,
        STATUS_WAITING_PARTS,
    }:
        await callback.answer(
            "Цю заявку вже не можна скасувати. Напишіть майстру.",
            show_alert=True,
        )
        return

    await callback.answer()
    await state.clear()
    await edit_or_send(
        callback,
        f"❓ <b>Скасувати заявку {request.number}?</b>\n\n"
        "Якщо ремонт уже почався, краще спочатку написати майстру.",
        cancel_confirm_keyboard(request.id),
    )


@router.callback_query(F.data.startswith("my:cancel_confirm:"))
async def my_cancel_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    try:
        request_id = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None or request.user_id != callback.from_user.id:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if request.status not in {
        STATUS_NEW,
        STATUS_ACCEPTED,
        STATUS_DIAGNOSTICS,
        STATUS_WAITING_PARTS,
    }:
        await callback.answer("Заявку вже не можна скасувати.", show_alert=True)
        return

    await state.clear()
    request = await set_status(request.id, STATUS_CANCELED, "Скасовано клієнтом")
    await callback.answer("Заявку скасовано")

    if request:
        await notify_admins_canceled(bot, request)
        await edit_or_send(
            callback,
            client_request_card(request),
            back_to_menu_keyboard(),
        )


# =========================================================
# ПОГОДЖЕННЯ ЦІНИ
# =========================================================

@router.callback_query(F.data.startswith("client:price_accept:"))
async def price_accept(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await _handle_price_decision(callback, state, bot, accepted=True)


@router.callback_query(F.data.startswith("client:price_decline:"))
async def price_decline(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await _handle_price_decision(callback, state, bot, accepted=False)


async def _handle_price_decision(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    accepted: bool,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 4:
        await callback.answer("Помилка.", show_alert=True)
        return

    try:
        request_id = int(parts[2])
        offered_price = int(parts[3])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None or request.user_id != callback.from_user.id:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if request.status in FINAL_STATUSES:
        await callback.answer(
            "Заявка вже закрита. Напишіть майстру, якщо потрібно щось змінити.",
            show_alert=True,
        )
        return

    if request.price_status != PRICE_STATUS_OFFERED:
        await callback.answer(
            "Ця пропозиція вже неактуальна.",
            show_alert=True,
        )
        return

    if request.price != offered_price:
        await callback.answer(
            "Ціна змінилася. Перегляньте нову пропозицію від майстра.",
            show_alert=True,
        )
        return

    await state.clear()
    updated = await set_price_decision(request.id, accepted)

    if updated is None:
        await callback.answer("Помилка.", show_alert=True)
        return

    await callback.answer()

    if accepted:
        text = (
            f"✅ <b>Ціну погоджено!</b>\n\n"
            f"Заявка: <b>{updated.number}</b>\n"
            f"Сума: <b>{format_money(updated.price)}</b>\n\n"
            "Майстер продовжить роботу. Стежити за статусом можна "
            "в розділі «Мої заявки»."
        )
    else:
        text = (
            f"❌ <b>Ціну відхилено.</b>\n\n"
            f"Заявка: <b>{updated.number}</b>\n\n"
            "Майстер зв'яжеться з вами, щоб уточнити деталі "
            "або запропонувати інший варіант."
        )

    await edit_or_send(callback, text, back_to_menu_keyboard())
    await notify_admins_price_decision(bot, updated, accepted)


# =========================================================
# ВІДГУКИ
# =========================================================

@router.callback_query(F.data.startswith("review:rate:"))
async def review_rate(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 4:
        await callback.answer("Помилка.", show_alert=True)
        return

    try:
        request_id = int(parts[2])
        rating = int(parts[3])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    if rating < 1 or rating > 5:
        await callback.answer("Оцінка має бути від 1 до 5.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None or request.user_id != callback.from_user.id:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if request.status != STATUS_DONE:
        await callback.answer("Оцінити можна після завершення.", show_alert=True)
        return

    if request.rating:
        await callback.answer("Ви вже оцінили цю заявку.", show_alert=True)
        return

    await state.clear()
    updated = await set_review(request.id, rating)
    await callback.answer("Дякуємо!")

    await edit_or_send(
        callback,
        f"⭐ <b>Оцінка: {rating}/5</b>\n\n"
        "Дякуємо! Хочете додати кілька слів про ремонт? "
        "Це необов'язково.",
        review_followup_keyboard(request.id),
    )

    if updated:
        await notify_admins_review(bot, updated)


@router.callback_query(F.data.startswith("review:text:"))
async def review_text_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 3:
        await callback.answer("Помилка.", show_alert=True)
        return

    try:
        request_id = int(parts[2])
    except ValueError:
        await callback.answer("Помилка.", show_alert=True)
        return

    request = await get_request(request_id)

    if request is None or request.user_id != callback.from_user.id:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if request.status != STATUS_DONE or not request.rating:
        await callback.answer(
            "Спочатку поставте оцінку за ремонт.",
            show_alert=True,
        )
        return

    await state.set_state(ReviewFlow.text)
    await state.update_data(review_request_id=request.id)
    await callback.answer()

    await edit_or_send(
        callback,
        "✍️ <b>Ваш відгук</b>\n\n"
        "Напишіть кілька слів про роботу майстра. "
        "Щоб передумати — натисніть «Пропустити» або /cancel.",
        review_text_keyboard(request.id),
    )


@router.callback_query(F.data.startswith("review:skip:"))
async def review_skip(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) == 3:
        try:
            request_id = int(parts[2])
        except ValueError:
            request_id = None

        if request_id is not None:
            request = await get_request(request_id)
            if request and request.user_id != callback.from_user.id:
                await callback.answer("Заявку не знайдено.", show_alert=True)
                return

    await state.clear()
    await callback.answer("Дякуємо!")
    await edit_or_send(callback, review_thanks_text())


@router.message(ReviewFlow.text, F.text)
async def review_text(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()
    request_id = data.get("review_request_id")

    if not isinstance(request_id, int):
        await state.clear()
        await message.answer("Дякуємо за відгук!")
        return

    text = (message.text or "").strip()

    if len(text) > MAX_REVIEW_LENGTH:
        await message.answer(
            f"Відгук занадто довгий. Максимум {MAX_REVIEW_LENGTH} символів."
        )
        return

    request = await get_request(request_id)

    if request is None or request.user_id != message.from_user.id:
        await state.clear()
        await message.answer("Дякуємо!")
        return

    if request.rating is None:
        await state.clear()
        await message.answer(
            "Спочатку поставте оцінку за ремонт, будь ласка."
        )
        return

    updated = await set_review(request.id, request.rating, text or None)
    await state.clear()

    await message.answer(review_thanks_text())

    if updated:
        await notify_admins_review(bot, updated, followup=True)


@router.message(ReviewFlow.text)
async def review_text_fallback(message: Message) -> None:
    await message.answer(
        "Напишіть відгук текстом, натисніть «Пропустити» "
        "або /cancel."
    )
