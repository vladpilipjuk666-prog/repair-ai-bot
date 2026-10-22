"""Вспомогательные функции: форматирование, валидация, разбор AI-ответа."""

from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from constants import (
    DEVICE_TYPES,
    PRICE_STATUS_LABELS,
    SERVICE_METHODS,
    STATUS_LABELS,
)

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def h(value: Any) -> str:
    """Экранирование пользовательского текста для HTML-разметки Telegram."""
    return html.escape(str(value if value is not None else ""), quote=False)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_dt(value: datetime | None) -> str:
    value = as_utc(value)
    if value is None:
        return "—"
    return value.astimezone(KYIV_TZ).strftime("%d.%m.%Y %H:%M")


def format_money(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", " ") + " грн"


def normalize_phone(raw: str | None) -> str | None:
    """Приводит телефон к виду +380XXXXXXXXX (или +<digits>)."""
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    if len(digits) == 10 and digits.startswith("0"):
        digits = "38" + digits

    if len(digits) == 11 and digits.startswith("80"):
        digits = "3" + digits

    if len(digits) == 12 and digits.startswith("380"):
        return "+" + digits

    if 10 <= len(digits) <= 15:
        return "+" + digits

    return None


def format_phone(phone: str | None) -> str:
    if not phone:
        return "—"

    digits = re.sub(r"\D", "", phone)
    if len(digits) == 12 and digits.startswith("380"):
        return (
            f"+380 {digits[3:5]} {digits[5:8]} "
            f"{digits[8:10]} {digits[10:12]}"
        )

    return phone


def parse_price(raw: str | None) -> int | None:
    """Достаёт число из строки вида «2 500 грн»."""
    if not raw:
        return None

    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return None

    try:
        value = int(digits)
    except ValueError:
        return None

    if value < 0 or value > 200_000:
        return None

    return value


def parse_json_object(text: str | None) -> dict[str, Any] | None:
    """Разбирает JSON, даже если модель обернула его в ```json ... ```."""
    if not text:
        return None

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    candidates = [cleaned]

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value

    return None


def validate_ai_estimate(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Проверяет и нормализует ответ AI. Возвращает None, если ответ бесполезен."""
    if not data:
        return None

    summary = str(data.get("summary") or "").strip()
    if not summary:
        return None

    def _number(key: str) -> int | None:
        try:
            value = int(float(str(data.get(key)).replace(" ", "").replace(",", ".")))
        except (TypeError, ValueError):
            return None
        return min(max(value, 0), 200_000)

    price_min = _number("price_min")
    price_max = _number("price_max")

    if price_min is None and price_max is None:
        price_min = price_max = None
    elif price_min is None:
        price_min = price_max
    elif price_max is None:
        price_max = price_min

    if price_min is not None and price_max is not None and price_max < price_min:
        price_min, price_max = price_max, price_min

    eta = str(data.get("eta") or "").strip()[:80]
    confidence = str(data.get("confidence") or "").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = ""

    return {
        "summary": summary[:600],
        "price_min": price_min,
        "price_max": price_max,
        "eta": eta,
        "confidence": confidence,
    }


def status_label(status: str | None) -> str:
    return STATUS_LABELS.get(status or "", status or "—")


def device_label(device_type: str | None) -> str:
    return DEVICE_TYPES.get(device_type or "", "Інша техніка")


def service_label(service_method: str | None) -> str:
    return SERVICE_METHODS.get(service_method or "", "Не вказано")


def price_status_label(price_status: str | None) -> str:
    return PRICE_STATUS_LABELS.get(price_status or "", "не вказана")


def rating_stars(rating: int | None) -> str:
    if not rating:
        return "—"
    rating = min(max(int(rating), 1), 5)
    return "⭐" * rating + "☆" * (5 - rating)


def truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def plural_requests(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "заявка"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "заявки"
    return "заявок"


def plural_reviews(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "відгук"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "відгуки"
    return "відгуків"
