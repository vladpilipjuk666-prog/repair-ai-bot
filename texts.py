"""Тексты сообщений бота (HTML)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from config import (
    CONTACT_NAME,
    CONTACT_PHONE,
    CONTACT_USERNAME,
    FAQ_ITEMS,
    PRICE_LIST,
    PRICE_NOTE,
    SERVICE_CITY,
    WORK_HOURS,
)
from constants import (
    PRICE_STATUS_ACCEPTED,
    STATUS_ACCEPTED,
    STATUS_CANCELED,
    STATUS_DECLINED,
    STATUS_DIAGNOSTICS,
    STATUS_DONE,
    STATUS_NEW,
    STATUS_READY,
    STATUS_WAITING_PARTS,
)
from utils import (
    device_label,
    format_dt,
    format_money,
    format_phone,
    h,
    plural_reviews,
    price_status_label,
    rating_stars,
    service_label,
    status_label,
    truncate,
)

if TYPE_CHECKING:
    from database import Request, RequestEvent


def main_menu_text(user_name: str, is_admin: bool = False) -> str:
    admin_note = (
        "\n\n⚙️ У вас є доступ до адмін-панелі майстра."
        if is_admin
        else ""
    )

    return (
        f"👋 <b>Вітаю, {h(user_name)}!</b>\n\n"
        f"Це бот майстерні <b>{h(CONTACT_NAME)}</b>.\n"
        f"🛠 Ремонт комп'ютерів, ноутбуків та іншої техніки "
        f"у {h(SERVICE_CITY)}.\n\n"
        "Оформіть заявку — майстер отримає її одразу, "
        "зв'яжеться з вами та підкаже ціну й строки.\n\n"
        "⏱ Заповнення займає 1–2 хвилини."
        f"{admin_note}"
    )


def help_text() -> str:
    return (
        "🛠 <b>Як працює бот</b>\n\n"
        "1. Натисніть <b>«Нова заявка»</b>.\n"
        "2. Оберіть техніку та опишіть проблему.\n"
        "3. Додайте фото (необов'язково).\n"
        "4. Вкажіть, як вам зручно передати техніку.\n"
        "5. Залиште ім'я та телефон.\n\n"
        "Після цього заявка одразу надійде майстру. "
        "Ви отримаєте номер заявки та зможете стежити за статусом.\n\n"
        "<b>Команди:</b>\n"
        "/start — головне меню\n"
        "/new — нова заявка\n"
        "/my — мої заявки\n"
        "/prices — орієнтовні ціни\n"
        "/contacts — контакти\n"
        "/faq — часті питання\n"
        "/reviews — відгуки клієнтів\n"
        "/cancel — скасувати заповнення"
    )


def prices_text() -> str:
    lines = "\n".join(
        f"• {h(name)} — <b>{h(price)}</b>" for name, price in PRICE_LIST
    )

    return (
        "💰 <b>Орієнтовні ціни</b>\n\n"
        f"{lines}\n\n"
        f"<i>{h(PRICE_NOTE)}</i>"
    )


def faq_text() -> str:
    blocks = [
        f"<b>{h(question)}</b>\n{h(answer)}"
        for question, answer in FAQ_ITEMS
    ]

    return (
        "❓ <b>Часті питання</b>\n\n"
        + "\n\n".join(blocks)
        + "\n\nНе знайшли відповідь? Напишіть майстру — контакти в меню."
    )


def contacts_text() -> str:
    lines = [
        "📞 <b>Контакти</b>",
        "",
        f"Майстерня: <b>{h(CONTACT_NAME)}</b>",
        f"📍 {h(SERVICE_CITY)}",
        f"🕘 {h(WORK_HOURS)}",
    ]

    if CONTACT_PHONE:
        phone_href = re.sub(r"[^\d+]", "", CONTACT_PHONE)
        lines.append(
            f"📱 <a href=\"tel:{h(phone_href)}\">"
            f"{h(format_phone(CONTACT_PHONE))}</a>"
        )

    if CONTACT_USERNAME:
        lines.append(
            f"💬 Telegram: <a href=\"https://t.me/{h(CONTACT_USERNAME)}\">"
            f"@{h(CONTACT_USERNAME)}</a>"
        )

    lines.extend(
        [
            "",
            "Найшвидший спосіб отримати ціну — оформити заявку в боті.",
        ]
    )

    return "\n".join(lines)


def reviews_text(
    reviews: list[Request],
    average: float,
    count: int,
) -> str:
    if not count:
        return (
            "⭐ <b>Відгуки клієнтів</b>\n\n"
            "Поки що відгуків немає.\n"
            "Станьте першим — оформіть заявку, і після ремонту "
            "зможете залишити оцінку."
        )

    lines = [
        "⭐ <b>Відгуки клієнтів</b>",
        "",
        f"Середня оцінка: <b>{average:.1f}/5</b> "
        f"({count} {plural_reviews(count)})",
        "",
    ]

    for request in reviews:
        first_name = (request.client_name or "Клієнт").split()[0]
        lines.append(
            f"{rating_stars(request.rating)} <b>{h(first_name)}</b> · "
            f"{h(device_label(request.device_type))}"
        )
        if request.review:
            lines.append(f"«{h(truncate(request.review, 300))}»")
        lines.append("")

    return "\n".join(lines).strip()


def my_requests_text(requests: list[Request]) -> str:
    if not requests:
        return (
            "📋 <b>Мої заявки</b>\n\n"
            "У вас поки немає заявок.\n"
            "Натисніть «Нова заявка», щоб створити першу."
        )

    lines = ["📋 <b>Мої заявки</b>", ""]

    for request in requests:
        lines.append(
            f"<b>{h(request.number)}</b> · {status_label(request.status)}\n"
            f"{h(device_label(request.device_type))} · "
            f"{h(format_dt(request.created_at))}"
        )

    lines.extend(
        [
            "",
            "Натисніть на заявку нижче, щоб побачити деталі.",
        ]
    )

    return "\n".join(lines)


def client_request_card(request: Request) -> str:
    lines = [
        f"🧾 <b>Заявка {h(request.number)}</b>",
        f"<b>Статус:</b> {status_label(request.status)}",
        "",
        f"{h(device_label(request.device_type))}"
        + (f" · {h(request.device_model)}" if request.device_model else ""),
        "",
        "<b>Проблема:</b>",
        h(truncate(request.problem, 900)),
        "",
        f"🚚 <b>Передача:</b> {h(service_label(request.service_method))}",
    ]

    if request.address:
        lines.append(f"📍 <b>Адреса:</b> {h(request.address)}")

    lines.append(f"📅 <b>Створено:</b> {h(format_dt(request.created_at))}")

    if request.ai_summary:
        lines.extend(
            [
                "",
                "🤖 <b>Попередній висновок AI:</b>",
                h(truncate(request.ai_summary, 450)),
            ]
        )
        if request.ai_price_min is not None and request.ai_price_max is not None:
            lines.append(
                f"Орієнтовно: <b>{format_money(request.ai_price_min)} – "
                f"{format_money(request.ai_price_max)}</b>"
            )

    if request.price is not None:
        lines.extend(
            [
                "",
                f"💰 <b>Ціна майстра:</b> {format_money(request.price)} "
                f"({price_status_label(request.price_status)})",
            ]
        )

    if request.master_comment:
        lines.extend(
            [
                "",
                "💬 <b>Коментар майстра:</b>",
                h(truncate(request.master_comment, 500)),
            ]
        )

    if request.rating:
        lines.extend(
            [
                "",
                f"⭐ <b>Ваша оцінка:</b> {rating_stars(request.rating)}",
            ]
        )
        if request.review:
            lines.append(f"«{h(truncate(request.review, 400))}»")

    return "\n".join(lines)


def admin_request_card(request: Request) -> str:
    username = f" · @{h(request.username)}" if request.username else ""
    client = (
        f'<a href="tg://user?id={request.user_id}">'
        f"{h(request.client_name)}</a>{username}"
    )

    lines = [
        f"🧾 <b>Заявка {h(request.number)}</b>",
        f"<b>Статус:</b> {status_label(request.status)}",
        "",
        f"👤 <b>Клієнт:</b> {client}",
        f"📱 <b>Телефон:</b> "
        f'<a href="tel:{h(request.phone)}">{h(format_phone(request.phone))}</a>',
        f"🆔 <b>Telegram ID:</b> <code>{request.user_id}</code>",
        "",
        f"🛠 <b>Техніка:</b> {h(device_label(request.device_type))}",
    ]

    if request.device_model:
        lines.append(f"🏷 <b>Модель:</b> {h(request.device_model)}")

    lines.extend(
        [
            "",
            "<b>Проблема:</b>",
            h(truncate(request.problem, 1500)),
            "",
            f"🚚 <b>Передача:</b> {h(service_label(request.service_method))}",
        ]
    )

    if request.address:
        lines.append(f"📍 <b>Адреса:</b> {h(request.address)}")

    lines.extend(
        [
            f"📸 <b>Фото:</b> {len(request.photos)}",
            f"📅 <b>Створено:</b> {h(format_dt(request.created_at))}",
        ]
    )

    if request.ai_summary:
        lines.extend(
            [
                "",
                "🤖 <b>AI-оцінка:</b>",
                h(truncate(request.ai_summary, 600)),
            ]
        )
        if request.ai_price_min is not None and request.ai_price_max is not None:
            lines.append(
                f"Орієнтир: <b>{format_money(request.ai_price_min)} – "
                f"{format_money(request.ai_price_max)}</b>"
            )
        if request.ai_eta:
            lines.append(f"⏱ Термін: {h(request.ai_eta)}")
        if request.ai_confidence:
            confidence = {
                "low": "низька",
                "medium": "середня",
                "high": "висока",
            }.get(request.ai_confidence, request.ai_confidence)
            lines.append(f"🎯 Впевненість: {h(confidence)}")

    lines.extend(
        [
            "",
            f"💰 <b>Ціна:</b> {format_money(request.price)} "
            f"({price_status_label(request.price_status)})",
        ]
    )

    if request.master_comment:
        lines.extend(
            [
                "",
                "💬 <b>Останній коментар:</b>",
                h(truncate(request.master_comment, 600)),
            ]
        )

    if request.rating:
        lines.extend(
            [
                "",
                f"⭐ <b>Оцінка клієнта:</b> {rating_stars(request.rating)}",
            ]
        )
        if request.review:
            lines.append(f"«{h(truncate(request.review, 500))}»")

    return "\n".join(lines)


def confirm_request_text(data: dict[str, Any]) -> str:
    ai = data.get("ai") or {}
    photos = data.get("photos") or []

    lines = [
        "✅ <b>Перевірте заявку</b>",
        "",
        f"🛠 <b>Техніка:</b> {h(device_label(data.get('device_type')))}",
    ]

    if data.get("device_model"):
        lines.append(f"🏷 <b>Модель:</b> {h(data['device_model'])}")

    lines.extend(
        [
            "",
            "<b>Проблема:</b>",
            h(truncate(data.get("problem", ""), 900)),
            "",
            f"🚚 <b>Передача:</b> {h(service_label(data.get('service_method')))}",
        ]
    )

    if data.get("address"):
        lines.append(f"📍 <b>Адреса:</b> {h(data['address'])}")

    lines.extend(
        [
            f"👤 <b>Ім'я:</b> {h(data.get('client_name', '—'))}",
            f"📱 <b>Телефон:</b> {h(format_phone(data.get('phone')))}",
            f"📸 <b>Фото:</b> {len(photos)}",
        ]
    )

    if ai.get("summary"):
        lines.extend(
            [
                "",
                "🤖 <b>Попередня оцінка AI:</b>",
                h(truncate(ai.get("summary"), 450)),
            ]
        )
        if ai.get("price_min") is not None and ai.get("price_max") is not None:
            lines.append(
                f"Орієнтовно: <b>{format_money(ai['price_min'])} – "
                f"{format_money(ai['price_max'])}</b>"
            )

    lines.extend(
        [
            "",
            "Після підтвердження заявка одразу надійде майстру.",
        ]
    )

    return "\n".join(lines)


def ai_estimate_text(estimate: dict[str, Any]) -> str:
    lines = [
        "🤖 <b>Попередній висновок AI</b>",
        "",
        h(estimate.get("summary") or ""),
    ]

    price_min = estimate.get("price_min")
    price_max = estimate.get("price_max")
    if price_min is not None and price_max is not None:
        if price_min == price_max:
            price = format_money(price_min)
        else:
            price = f"{format_money(price_min)} – {format_money(price_max)}"
        lines.extend(["", f"💰 <b>Орієнтовно:</b> {price}"])

    if estimate.get("eta"):
        lines.append(f"⏱ <b>Термін:</b> {h(estimate['eta'])}")

    lines.extend(
        [
            "",
            "<i>Це попередня оцінка, а не остаточна ціна. "
            "Точна вартість — після діагностики. "
            "Вартість запчастин може додаватися окремо.</i>",
        ]
    )

    return "\n".join(lines)


def new_request_client_text(request: Request) -> str:
    return (
        f"✅ <b>Заявку {h(request.number)} прийнято!</b>\n\n"
        f"🛠 {h(device_label(request.device_type))}"
        + (f" · {h(request.device_model)}" if request.device_model else "")
        + "\n"
        f"📋 Статус: {status_label(request.status)}\n\n"
        "Майстер отримав заявку та зв'яжеться з вами найближчим часом.\n"
        "Стежити за статусом можна в розділі «Мої заявки»."
    )


def status_client_text(request: Request, status: str) -> str:
    number = h(request.number)

    messages = {
        STATUS_ACCEPTED: (
            f"🛠 <b>Заявку {number} прийнято в роботу.</b>\n\n"
            "Майстер уже займається вашою технікою. "
            "Якщо потрібно щось уточнити — напишіть у цей чат."
        ),
        STATUS_DIAGNOSTICS: (
            f"🔍 <b>За заявкою {number} почалася діагностика.</b>\n\n"
            "Перевіряємо техніку та визначаємо причину несправності. "
            "Про результат повідомимо тут."
        ),
        STATUS_WAITING_PARTS: (
            f"📦 <b>За заявкою {number} чекаємо деталь.</b>\n\n"
            "Замовлення вже в роботі. Повідомимо, щойно деталь надійде."
        ),
        STATUS_READY: (
            f"✅ <b>Ваша техніка за заявкою {number} готова до видачі.</b>\n\n"
            "Можна узгодити час отримання з майстром."
            + (
                f"\n\n💰 До сплати: <b>{format_money(request.price)}</b>"
                if request.price is not None
                and request.price_status == PRICE_STATUS_ACCEPTED
                else ""
            )
        ),
        STATUS_DONE: (
            f"🏁 <b>Ремонт за заявкою {number} завершено.</b>\n\n"
            "Дякуємо, що звернулися! Будемо вдячні за оцінку роботи."
        ),
        STATUS_DECLINED: (
            f"❌ <b>На жаль, заявку {number} не вдалося прийняти.</b>\n\n"
            "Майстер зв'яжеться з вами, щоб пояснити причину "
            "та підказати подальші кроки."
        ),
        STATUS_CANCELED: (
            f"🚫 <b>Заявку {number} скасовано.</b>\n\n"
            "Якщо це сталося помилково — створіть нову заявку "
            "або напишіть майстру."
        ),
    }

    return messages.get(status, f"Статус заявки {number}: {status_label(status)}")


def price_offer_text(request: Request) -> str:
    lines = [
        "💰 <b>Пропозиція ціни</b>",
        "",
        f"Заявка: <b>{h(request.number)}</b>",
        f"Майстер пропонує: <b>{format_money(request.price)}</b>",
    ]

    if request.master_comment:
        lines.extend(
            [
                "",
                "💬 <b>Коментар:</b>",
                h(truncate(request.master_comment, 600)),
            ]
        )

    lines.extend(
        [
            "",
            "Погоджуєте ціну?",
            "<i>Якщо ні — майстер може запропонувати інший варіант "
            "або уточнити деталі.</i>",
        ]
    )

    return "\n".join(lines)


def price_decision_admin_text(request: Request, accepted: bool) -> str:
    action = "погодив" if accepted else "відхилив"
    emoji = "✅" if accepted else "❌"

    return (
        f"{emoji} <b>Клієнт {action} ціну</b>\n\n"
        f"Заявка: <b>{h(request.number)}</b>\n"
        f"Клієнт: {h(request.client_name)}\n"
        f"Ціна: <b>{format_money(request.price)}</b>"
    )


def review_prompt_text(request: Request) -> str:
    return (
        "⭐ <b>Як вам ремонт?</b>\n\n"
        f"Оцініть, будь ласка, роботу за заявкою "
        f"<b>{h(request.number)}</b> від 1 до 5.\n\n"
        "Ваша оцінка допомагає іншим клієнтам."
    )


def review_thanks_text() -> str:
    return (
        "🙏 <b>Дякуємо за відгук!</b>\n\n"
        "Нам важлива ваша думка. Гарного дня!"
    )


def admin_review_notification(
    request: Request,
    followup: bool = False,
) -> str:
    title = (
        "💬 <b>Клієнт доповнив відгук</b>"
        if followup
        else "⭐ <b>Новий відгук клієнта</b>"
    )
    lines = [
        title,
        "",
        f"Заявка: <b>{h(request.number)}</b>",
        f"Клієнт: {h(request.client_name)}",
        f"Оцінка: {rating_stars(request.rating)}",
    ]

    if request.review:
        lines.extend(["", f"«{h(truncate(request.review, 700))}»"])

    return "\n".join(lines)


def request_history_text(
    request: Request,
    events: list[RequestEvent],
) -> str:
    lines = [
        f"🕘 <b>Історія заявки {h(request.number)}</b>",
        "",
        f"Поточний статус: {status_label(request.status)}",
        "",
    ]

    if not events:
        lines.append("Записів історії поки немає.")
        return "\n".join(lines)

    for event in events:
        lines.append(
            f"• {h(format_dt(event.created_at))} — "
            f"{status_label(event.status)}"
        )
        if event.comment:
            lines.append(f"  <i>{h(truncate(event.comment, 200))}</i>")

    return "\n".join(lines)


def stats_text(stats: dict[str, Any]) -> str:
    counts = stats.get("counts", {})
    total = stats.get("total", 0)
    done = stats.get("done", 0)
    revenue = stats.get("revenue", 0)
    paid = stats.get("paid", 0)
    average_check = stats.get("average_check", int(revenue / paid) if paid else 0)

    status_lines = []
    for status, count in (
        (STATUS_NEW, counts.get(STATUS_NEW, 0)),
        (STATUS_ACCEPTED, counts.get(STATUS_ACCEPTED, 0)),
        (STATUS_DIAGNOSTICS, counts.get(STATUS_DIAGNOSTICS, 0)),
        (STATUS_WAITING_PARTS, counts.get(STATUS_WAITING_PARTS, 0)),
        (STATUS_READY, counts.get(STATUS_READY, 0)),
        (STATUS_DONE, counts.get(STATUS_DONE, 0)),
        (STATUS_DECLINED, counts.get(STATUS_DECLINED, 0)),
        (STATUS_CANCELED, counts.get(STATUS_CANCELED, 0)),
    ):
        if count:
            status_lines.append(f"{status_label(status)}: <b>{count}</b>")

    lines = [
        "📊 <b>Статистика майстерні</b>",
        "",
        f"Усього заявок: <b>{total}</b>",
        f"Активних: <b>{stats.get('active', 0)}</b>",
        f"Нових за 7 днів: <b>{stats.get('new_week', 0)}</b>",
        f"Завершено: <b>{done}</b>",
        f"Конверсія в завершення: <b>{stats.get('conversion', 0)}%</b>",
        "",
        f"💰 Виручка (погоджені ціни): <b>{format_money(revenue)}</b>",
        f"🧾 Середній чек: <b>{format_money(average_check)}</b>",
        (
            f"⭐ Середня оцінка: <b>{stats.get('avg_rating', 0):.1f}/5</b> "
            f"({stats.get('rated', 0)})"
        ),
    ]

    if status_lines:
        lines.extend(["", "<b>За статусами:</b>", *status_lines])

    return "\n".join(lines)


def admin_menu_text(stats: dict[str, Any]) -> str:
    counts = stats.get("counts", {})

    return (
        "⚙️ <b>Адмін-панель</b>\n\n"
        f"🆕 Нові: <b>{counts.get(STATUS_NEW, 0)}</b>\n"
        f"🔧 Активні: <b>{stats.get('active', 0)}</b>\n"
        f"🏁 Завершені: <b>{stats.get('done', 0)}</b>\n"
        f"📅 Нові за 7 днів: <b>{stats.get('new_week', 0)}</b>\n\n"
        f"💰 Виручка: <b>{format_money(stats.get('revenue', 0))}</b>\n"
        f"⭐ Середня оцінка: <b>{stats.get('avg_rating', 0):.1f}/5</b>\n\n"
        "Оберіть розділ:"
    )


def admin_list_text(
    scope: str,
    requests: list[Request],
    page: int,
    total: int,
    page_size: int = 8,
) -> str:
    titles = {
        "new": "🆕 Нові заявки",
        "active": "🔧 Активні заявки",
        "all": "📋 Усі заявки",
    }
    title = titles.get(scope, "Заявки")

    pages = max(1, (total + page_size - 1) // page_size)

    lines = [
        f"<b>{title}</b>",
        f"Усього: {total} · Сторінка {page + 1}/{pages}",
        "",
    ]

    if not requests:
        lines.append("Заявок у цьому розділі немає.")
        return "\n".join(lines)

    for request in requests:
        lines.append(
            f"<b>{h(request.number)}</b> · {status_label(request.status)}\n"
            f"{h(device_label(request.device_type))} · "
            f"{h(request.client_name)} · {h(format_dt(request.created_at))}"
        )

    lines.extend(["", "Натисніть на номер заявки нижче, щоб відкрити картку."])

    return "\n".join(lines)
