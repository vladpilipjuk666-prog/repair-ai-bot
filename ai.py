"""AI-оценка заявки через OpenRouter (бесплатные модели).

AI не является обязательным: если ключа нет или модель недоступна,
бот продолжает работать, а заявка просто уходит мастеру без оценки.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

from openai import AsyncOpenAI

from config import (
    AI_ENABLED,
    AI_MODEL,
    AI_TIMEOUT_SECONDS,
    OPENROUTER_API_KEY,
    PRICE_LIST,
)
from image_tools import prepare_image_for_ai
from utils import device_label, parse_json_object, validate_ai_estimate

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
if AI_ENABLED:
    _client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/vladpilipjuk666-prog/repair-ai-bot",
            "X-Title": "Pilipuk Repair Bot",
        },
    )


def _build_prompt(
    device_type: str,
    device_model: str | None,
    problem: str,
) -> str:
    price_reference = "\n".join(
        f"- {name}: {price}" for name, price in PRICE_LIST
    )

    return f"""
Ти — досвідчений майстер із ремонту комп'ютерів та ноутбуків у Києві.
Клієнт описав проблему. Зроби ПОПЕРЕДНЮ оцінку для майстерні.

Дані клієнта:
- Тип техніки: {device_label(device_type)}
- Модель: {device_model or "не вказана"}
- Опис проблеми: {problem}

Орієнтовний прайс майстерні (вартість роботи, без запчастин):
{price_reference}

Правила:
1. Не став остаточний діагноз і не обіцяй точну ціну.
2. Якщо даних мало — зроби ширший діапазон ціни.
3. Враховуй, що вартість запчастин оплачується окремо.
4. Пиши українською, просто і професійно.
5. Summary — 1–2 короткі речення: що ймовірно сталося і що треба перевірити.
6. Ціни — цілі числа в гривнях.
7. Якщо на фото видно конкретну проблему — згадай це в summary.

Поверни ТІЛЬКИ валідний JSON без markdown:
{{
  "summary": "короткий попередній висновок",
  "price_min": 0,
  "price_max": 0,
  "eta": "орієнтовний термін, наприклад 1–2 дні",
  "confidence": "low | medium | high"
}}
""".strip()


async def _request(
    prompt: str,
    images: list[bytes],
) -> str | None:
    if _client is None:
        return None

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

    for image in images[:3]:
        prepared = prepare_image_for_ai(image)
        encoded = base64.b64encode(prepared).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            }
        )

    response = await asyncio.wait_for(
        _client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": content}],
            temperature=0.2,
            max_tokens=500,
        ),
        timeout=AI_TIMEOUT_SECONDS,
    )

    if not response.choices:
        return None

    return response.choices[0].message.content


async def estimate_repair(
    device_type: str,
    device_model: str | None,
    problem: str,
    images: list[bytes] | None = None,
) -> dict[str, Any] | None:
    """Возвращает {summary, price_min, price_max, eta, confidence} или None."""
    if not AI_ENABLED or _client is None:
        return None

    prompt = _build_prompt(device_type, device_model, problem)
    images = images or []

    try:
        raw = await _request(prompt, images)
    except TimeoutError:
        logger.warning("AI-оценка не уложилась в таймаут")
        return None
    except Exception as error:
        logger.warning("AI-оценка с фото не удалась: %s", error)

        if not images:
            return None

        # Некоторые бесплатные модели не поддерживают изображения.
        # Пробуем ещё раз только по тексту.
        try:
            raw = await _request(prompt, [])
        except Exception as retry_error:
            logger.warning("AI-оценка без фото тоже не удалась: %s", retry_error)
            return None

    estimate = validate_ai_estimate(parse_json_object(raw))
    if estimate is None:
        logger.warning("AI вернул ответ, который не удалось разобрать: %r", raw)

    return estimate
