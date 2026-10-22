"""Константы: статусы, типы устройств, способы передачи техники."""

from __future__ import annotations

STATUS_NEW = "new"
STATUS_ACCEPTED = "accepted"
STATUS_DIAGNOSTICS = "diagnostics"
STATUS_WAITING_PARTS = "waiting_parts"
STATUS_READY = "ready"
STATUS_DONE = "done"
STATUS_DECLINED = "declined"
STATUS_CANCELED = "canceled"

STATUS_LABELS: dict[str, str] = {
    STATUS_NEW: "🆕 Нова",
    STATUS_ACCEPTED: "🛠 В роботі",
    STATUS_DIAGNOSTICS: "🔍 Діагностика",
    STATUS_WAITING_PARTS: "📦 Чекаємо деталі",
    STATUS_READY: "✅ Готова до видачі",
    STATUS_DONE: "🏁 Завершена",
    STATUS_DECLINED: "❌ Відхилена",
    STATUS_CANCELED: "🚫 Скасована",
}

# Статусы, при которых заявка считается активной.
ACTIVE_STATUSES: tuple[str, ...] = (
    STATUS_NEW,
    STATUS_ACCEPTED,
    STATUS_DIAGNOSTICS,
    STATUS_WAITING_PARTS,
    STATUS_READY,
)

FINAL_STATUSES: tuple[str, ...] = (
    STATUS_DONE,
    STATUS_DECLINED,
    STATUS_CANCELED,
)

# Какие переходы разрешены админу. Кнопки строятся из этого же словаря.
STATUS_ACTIONS: dict[str, tuple[str, ...]] = {
    STATUS_NEW: (STATUS_ACCEPTED, STATUS_DIAGNOSTICS, STATUS_DECLINED),
    STATUS_ACCEPTED: (
        STATUS_DIAGNOSTICS,
        STATUS_WAITING_PARTS,
        STATUS_READY,
        STATUS_DONE,
        STATUS_DECLINED,
    ),
    STATUS_DIAGNOSTICS: (
        STATUS_WAITING_PARTS,
        STATUS_READY,
        STATUS_DONE,
        STATUS_DECLINED,
    ),
    STATUS_WAITING_PARTS: (STATUS_READY, STATUS_DONE, STATUS_DECLINED),
    STATUS_READY: (STATUS_DONE, STATUS_DECLINED),
    STATUS_DONE: (),
    STATUS_DECLINED: (),
    STATUS_CANCELED: (),
}

STATUS_ACTION_LABELS: dict[str, str] = {
    STATUS_ACCEPTED: "🛠 В роботу",
    STATUS_DIAGNOSTICS: "🔍 Діагностика",
    STATUS_WAITING_PARTS: "📦 Чекаємо деталі",
    STATUS_READY: "✅ Готова",
    STATUS_DONE: "🏁 Завершити",
    STATUS_DECLINED: "❌ Відхилити",
}

PRICE_STATUS_NONE = "none"
PRICE_STATUS_OFFERED = "offered"
PRICE_STATUS_ACCEPTED = "accepted"
PRICE_STATUS_DECLINED = "declined"

PRICE_STATUS_LABELS: dict[str, str] = {
    PRICE_STATUS_NONE: "не вказана",
    PRICE_STATUS_OFFERED: "💰 очікує підтвердження",
    PRICE_STATUS_ACCEPTED: "✅ погоджена",
    PRICE_STATUS_DECLINED: "❌ відхилена клієнтом",
}

DEVICE_TYPES: dict[str, str] = {
    "laptop": "💻 Ноутбук",
    "pc": "🖥 Комп'ютер",
    "other": "📱 Інша техніка",
}

SERVICE_METHODS: dict[str, str] = {
    "dropoff": "🚶 Привезу самостійно",
    "courier": "🚚 Кур'єр по Києву",
    "onsite": "🏠 Виїзд майстра",
}

# Способы, для которых нужен адрес.
ADDRESS_REQUIRED: tuple[str, ...] = ("courier", "onsite")
