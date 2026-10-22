"""Inline- и reply-клавиатуры."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import CONTACT_USERNAME, MAX_PHOTOS
from constants import (
    FINAL_STATUSES,
    PRICE_STATUS_OFFERED,
    STATUS_ACCEPTED,
    STATUS_ACTION_LABELS,
    STATUS_ACTIONS,
    STATUS_DECLINED,
    STATUS_DIAGNOSTICS,
    STATUS_NEW,
    STATUS_WAITING_PARTS,
)
from utils import device_label, status_label

if TYPE_CHECKING:
    from database import Request


def _markup(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [_button("🛠 Нова заявка", "menu:new")],
        [
            _button("📋 Мої заявки", "menu:my"),
            _button("💰 Ціни", "menu:prices"),
        ],
        [
            _button("⭐ Відгуки", "menu:reviews"),
            _button("❓ FAQ", "menu:faq"),
        ],
        [_button("📞 Контакти", "menu:contacts")],
    ]

    if is_admin:
        rows.append([_button("⚙️ Адмін-панель", "admin:menu")])

    return _markup(rows)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return _markup([[_button("⬅️ Головне меню", "menu:main")]])


def contacts_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if CONTACT_USERNAME:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 Написати майстру",
                    url=f"https://t.me/{CONTACT_USERNAME}",
                )
            ]
        )

    rows.append([_button("🛠 Нова заявка", "menu:new")])
    rows.append([_button("⬅️ Головне меню", "menu:main")])
    return _markup(rows)


def device_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("💻 Ноутбук", "device:laptop")],
            [_button("🖥 Комп'ютер", "device:pc")],
            [_button("📱 Інша техніка", "device:other")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def model_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("⏭ Не знаю / пропустити", "flow:skip_model")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def photos_keyboard(count: int) -> InlineKeyboardMarkup:
    done_text = (
        f"✅ Далі ({count}/{MAX_PHOTOS})"
        if count
        else "⏭ Далі без фото"
    )
    return _markup(
        [
            [_button(done_text, "flow:photos_done")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def service_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("🚶 Привезу самостійно", "service:dropoff")],
            [_button("🚚 Кур'єр по Києву", "service:courier")],
            [_button("🏠 Виїзд майстра", "service:onsite")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def address_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("⏭ Уточнимо в чаті", "flow:skip_address")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def name_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("👤 Використати ім'я з Telegram", "flow:name_tg")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Надіслати свій номер",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Або введіть номер вручну",
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("✅ Підтвердити заявку", "flow:confirm")],
            [_button("✏️ Заповнити заново", "flow:restart")],
            [_button("❌ Скасувати", "flow:cancel")],
        ]
    )


def my_requests_keyboard(requests: list[Request]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for request in requests:
        label = (
            f"{request.number} · {status_label(request.status)} · "
            f"{device_label(request.device_type)}"
        )
        rows.append([_button(label[:64], f"my:view:{request.id}")])

    rows.append([_button("⬅️ Головне меню", "menu:main")])
    return _markup(rows)


def request_detail_keyboard(request: Request) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if (
        request.price_status == PRICE_STATUS_OFFERED
        and request.status not in FINAL_STATUSES
    ):
        offered_price = request.price if request.price is not None else 0
        rows.append(
            [
                _button(
                    "✅ Погодити ціну",
                    f"client:price_accept:{request.id}:{offered_price}",
                ),
                _button(
                    "❌ Відхилити",
                    f"client:price_decline:{request.id}:{offered_price}",
                ),
            ]
        )

    if request.status in {
        STATUS_NEW,
        STATUS_ACCEPTED,
        STATUS_DIAGNOSTICS,
        STATUS_WAITING_PARTS,
    }:
        rows.append(
            [_button("❌ Скасувати заявку", f"my:cancel:{request.id}")]
        )

    rows.append([_button("⬅️ До моїх заявок", "my:list")])
    return _markup(rows)


def cancel_confirm_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return _markup(
        [
            [
                _button(
                    "✅ Так, скасувати",
                    f"my:cancel_confirm:{request_id}",
                )
            ],
            [_button("↩️ Ні, залишити", f"my:view:{request_id}")],
        ]
    )


def review_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return _markup(
        [
            [
                _button(f"{value} ⭐", f"review:rate:{request_id}:{value}")
                for value in range(1, 6)
            ]
        ]
    )


def review_followup_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("✍️ Додати текст", f"review:text:{request_id}")],
            [_button("⏭ Пропустити", f"review:skip:{request_id}")],
        ]
    )


def review_text_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return _markup(
        [[_button("⏭ Пропустити", f"review:skip:{request_id}")]]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [
            [
                _button("🆕 Нові", "admin:list:new:0"),
                _button("🔧 Активні", "admin:list:active:0"),
            ],
            [
                _button("📊 Статистика", "admin:stats"),
                _button("📤 Експорт CSV", "admin:export"),
            ],
            [
                _button("⭐ Відгуки", "admin:reviews"),
                _button("📋 Усі заявки", "admin:list:all:0"),
            ],
            [_button("🌐 Головне меню", "menu:main")],
        ]
    )


def admin_request_keyboard(request: Request) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    actions = [
        status
        for status in STATUS_ACTIONS.get(request.status, ())
        if status != STATUS_DECLINED
    ]

    # Кнопки статусов по две в ряд.
    for index in range(0, len(actions), 2):
        chunk = actions[index : index + 2]
        rows.append(
            [
                _button(
                    STATUS_ACTION_LABELS.get(status, status),
                    f"admin:status:{request.id}:{status}",
                )
                for status in chunk
            ]
        )

    action_row: list[InlineKeyboardButton] = []

    if request.status not in FINAL_STATUSES:
        price_label = (
            "💰 Змінити ціну"
            if request.price is not None
            else "💰 Вказати ціну"
        )
        action_row.append(
            _button(price_label, f"admin:price:{request.id}")
        )

    action_row.append(
        _button("💬 Написати клієнту", f"admin:message:{request.id}")
    )
    rows.append(action_row)

    if request.photos:
        rows.append(
            [
                _button(
                    f"📸 Показати фото ({len(request.photos)})",
                    f"admin:photos:{request.id}",
                )
            ]
        )

    if STATUS_DECLINED in STATUS_ACTIONS.get(request.status, ()):
        rows.append(
            [
                _button(
                    "❌ Відхилити заявку",
                    f"admin:status:{request.id}:{STATUS_DECLINED}",
                )
            ]
        )

    rows.append(
        [_button("🕘 Історія заявки", f"admin:history:{request.id}")]
    )
    rows.append(
        [
            _button("🔄 Оновити картку", f"admin:view:{request.id}"),
            _button("🏠 Адмін-панель", "admin:menu"),
        ]
    )
    return _markup(rows)


def admin_list_keyboard(
    requests: list[Request],
    scope: str,
    page: int,
    total: int,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for request in requests:
        rows.append(
            [_button(request.number, f"admin:view:{request.id}")]
        )

    nav: list[InlineKeyboardButton] = []

    if page > 0:
        nav.append(
            _button("⬅️", f"admin:list:{scope}:{page - 1}")
        )

    nav.append(_button("🏠 Адмін-панель", "admin:menu"))

    if (page + 1) * page_size < total:
        nav.append(
            _button("➡️", f"admin:list:{scope}:{page + 1}")
        )

    rows.append(nav)
    return _markup(rows)


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [[_button("⬅️ Адмін-панель", "admin:menu")]]
    )


def admin_price_comment_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return _markup(
        [
            [_button("⏭ Без коментаря", f"admin:price_skip:{request_id}")],
            [_button("❌ Скасувати", "admin:cancel")],
        ]
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return _markup(
        [[_button("❌ Скасувати", "admin:cancel")]]
    )


def price_offer_keyboard(
    request_id: int,
    price: int,
) -> InlineKeyboardMarkup:
    return _markup(
        [
            [
                _button(
                    "✅ Погоджуюсь",
                    f"client:price_accept:{request_id}:{price}",
                ),
                _button(
                    "❌ Не погоджуюсь",
                    f"client:price_decline:{request_id}:{price}",
                ),
            ]
        ]
    )
