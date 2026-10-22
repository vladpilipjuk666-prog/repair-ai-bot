"""Конфигурация бота.

Все секреты и настройки берутся из переменных окружения (.env локально
или Environment Variables на хостинге).
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _int_env(name: str, default: int = 0) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _int_list_env(name: str) -> list[int]:
    result: list[int] = []
    for chunk in _env(name).replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            result.append(int(chunk))
        except ValueError:
            continue
    return result


# =========================================================
# TELEGRAM
# =========================================================

# BOT_TOKEN — актуальное имя. TELEGRAM_BOT_TOKEN поддерживается,
# чтобы можно было переиспользовать старый .env.
BOT_TOKEN = _env("BOT_TOKEN") or _env("TELEGRAM_BOT_TOKEN")

OWNER_ID = _int_env("OWNER_ID")
ADMIN_IDS = sorted({OWNER_ID, *_int_list_env("ADMIN_IDS")} - {0})


def is_admin(user_id: int | None) -> bool:
    return bool(user_id) and user_id in ADMIN_IDS


# =========================================================
# БРЕНДИНГ / КОНТАКТЫ
# =========================================================

CONTACT_NAME = _env("CONTACT_NAME", "Pilipuk Repair")
_contact_username = _env("CONTACT_USERNAME", "pilipuk_repair")
CONTACT_USERNAME = re.sub(
    r"[^A-Za-z0-9_]",
    "",
    _contact_username.lstrip("@").rsplit("/", 1)[-1],
)
CONTACT_PHONE = _env("CONTACT_PHONE")
SERVICE_CITY = _env("SERVICE_CITY", "Київ")
WORK_HOURS = _env("WORK_HOURS", "Пн–Сб, 10:00–19:00")

BOT_SHORT_DESCRIPTION = (
    "Майстер з ремонту ПК та ноутбуків у Києві. "
    "Оформіть заявку — підкажу ціну та строки."
)

BOT_DESCRIPTION = (
    f"{CONTACT_NAME} — ремонт комп'ютерів, ноутбуків та іншої техніки "
    f"у {SERVICE_CITY}.\n\n"
    "Оформіть заявку прямо в боті: опишіть проблему, додайте фото — "
    "майстер отримає її одразу, зв'яжеться з вами та підкаже "
    "орієнтовну ціну.\n\n"
    "Діагностика, чистка, встановлення Windows, заміна комплектуючих, "
    "ремонт після залиття та інші роботи."
)


# =========================================================
# AI (OpenRouter)
# =========================================================

OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
AI_MODEL = _env("AI_MODEL", "openrouter/free")
AI_ENABLED = bool(OPENROUTER_API_KEY)
AI_TIMEOUT_SECONDS = _int_env("AI_TIMEOUT_SECONDS", 45)


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def _normalize_database_url(value: str) -> str:
    value = value.strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


DATABASE_URL = _normalize_database_url(
    _env("DATABASE_URL")
    or f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'repair_bot.db').as_posix()}"
)


# =========================================================
# WEBHOOK / SERVER
# =========================================================

PORT = _int_env("PORT", 8080)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = (
    _env("WEBHOOK_URL") or _env("RENDER_EXTERNAL_URL") or ""
).rstrip("/")

# Telegram secret_token: A-Z, a-z, 0-9, _ и -, до 256 символов.
# Если не задан, детерминированно выводим из токена бота.
_webhook_secret = re.sub(r"[^A-Za-z0-9_-]", "", _env("WEBHOOK_SECRET"))[:256]
WEBHOOK_SECRET = _webhook_secret or hashlib.sha256(
    BOT_TOKEN.encode("utf-8")
).hexdigest()[:32]


# =========================================================
# ЛИМИТЫ
# =========================================================

MAX_ACTIVE_REQUESTS = min(max(_int_env("MAX_ACTIVE_REQUESTS", 3), 1), 10)
MAX_PHOTOS = min(max(_int_env("MAX_PHOTOS", 5), 1), 10)

MAX_PROBLEM_LENGTH = 2000
MAX_NAME_LENGTH = 120
MAX_ADDRESS_LENGTH = 300
MAX_MODEL_LENGTH = 120
MAX_REVIEW_LENGTH = 1000

LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()


# =========================================================
# ПРАЙС И FAQ
# =========================================================

PRICE_LIST: list[tuple[str, str]] = [
    ("Діагностика", "300–500 грн"),
    ("Чистка від пилу + термопаста", "700–1200 грн"),
    ("Встановлення Windows / програм", "500–900 грн"),
    ("Заміна SSD / HDD", "700–1200 грн + деталь"),
    ("Заміна екрана ноутбука", "1500–4000 грн + матриця"),
    ("Заміна клавіатури", "800–2000 грн + деталь"),
    ("Заміна акумулятора", "1000–2500 грн + деталь"),
    ("Ремонт роз'єму живлення", "800–1800 грн"),
    ("Ремонт материнської плати", "від 2000 грн"),
]

PRICE_NOTE = (
    "Це орієнтовна вартість роботи без урахування запчастин. "
    "Точна ціна — після діагностики."
)

FAQ_ITEMS: list[tuple[str, str]] = [
    (
        "Скільки триває діагностика?",
        "Зазвичай 1–2 години. У складних випадках — до 1 дня. "
        "Про результат повідомимо в цьому чаті.",
    ),
    (
        "Чи можна передати техніку кур'єром?",
        "Так, по Києву. Оберіть «Кур'єр» при оформленні заявки — "
        "майстер узгодить час і адресу.",
    ),
    (
        "Чи є виїзд майстра?",
        "Так, по Києву. Оберіть «Виїзд майстра» у заявці.",
    ),
    (
        "Чи даєте гарантію?",
        "Так, на виконану роботу. Термін гарантії залежить від виду "
        "ремонту та комплектуючих — майстер повідомить після діагностики.",
    ),
    (
        "Чи ремонтуєте техніку після залиття?",
        "Так. Спочатку проводимо діагностику та узгоджуємо вартість "
        "робіт. Якщо ремонт недоцільний — чесно скажемо.",
    ),
    (
        "Як відбувається оплата?",
        "Після перевірки техніки. Готівкою або карткою — "
        "як домовитесь із майстром.",
    ),
]


# =========================================================
# ВАЛИДАЦИЯ
# =========================================================

def validate_config() -> None:
    missing: list[str] = []

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not ADMIN_IDS:
        missing.append("OWNER_ID (или ADMIN_IDS)")

    if missing:
        raise RuntimeError(
            "Не хватает переменных окружения: "
            + ", ".join(missing)
            + ". Заполните .env (локально) или Environment Variables "
            "(на хостинге)."
        )
