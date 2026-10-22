"""Уведомления клиентам и администраторам."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    InlineKeyboardMarkup,
    InputMediaPhoto,
)

from config import ADMIN_IDS
from constants import STATUS_DONE
from keyboards import (
    admin_request_keyboard,
    price_offer_keyboard,
    review_keyboard,
)
from texts import (
    admin_request_card,
    admin_review_notification,
    price_decision_admin_text,
    price_offer_text,
    review_prompt_text,
    status_client_text,
)
from utils import h

if TYPE_CHECKING:
    from database import Request

logger = logging.getLogger(__name__)


async def send_client_message(
    bot: Bot,
    user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return True
    except TelegramForbiddenError:
        logger.warning("Клиент %s заблокировал бота", user_id)
    except TelegramBadRequest as error:
        logger.warning("Не удалось отправить сообщение клиенту %s: %s", user_id, error)
    except Exception:
        logger.exception("Ошибка отправки клиенту %s", user_id)
    return False


async def notify_admins_text(
    bot: Bot,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    for admin_id in ADMIN_IDS:
        await send_client_message(bot, admin_id, text, reply_markup)


async def send_request_photos(
    bot: Bot,
    chat_id: int,
    photos: list[str],
) -> bool:
    if not photos:
        return False

    try:
        if len(photos) == 1:
            await bot.send_photo(chat_id, photo=photos[0])
        else:
            await bot.send_media_group(
                chat_id,
                media=[
                    InputMediaPhoto(media=photo)
                    for photo in photos[:10]
                ],
            )
        return True
    except Exception as error:
        logger.warning(
            "Не удалось отправить фото в чат %s: %s",
            chat_id,
            error,
        )
        return False


async def notify_admins_new_request(
    bot: Bot,
    request: Request,
) -> None:
    photos = request.photos[:10]

    for admin_id in ADMIN_IDS:
        sent = await send_client_message(
            bot,
            admin_id,
            admin_request_card(request),
            admin_request_keyboard(request),
        )
        if not sent or not photos:
            continue

        await send_request_photos(bot, admin_id, photos)


async def send_status_notification(
    bot: Bot,
    request: Request,
    status: str,
) -> None:
    text = status_client_text(request, status)

    if status == STATUS_DONE and not request.rating:
        text += "\n\n" + review_prompt_text(request)
        await send_client_message(
            bot,
            request.user_id,
            text,
            review_keyboard(request.id),
        )
        return

    await send_client_message(bot, request.user_id, text)


async def send_price_offer(
    bot: Bot,
    request: Request,
) -> bool:
    return await send_client_message(
        bot,
        request.user_id,
        price_offer_text(request),
        price_offer_keyboard(request.id, request.price or 0),
    )


async def notify_admins_price_decision(
    bot: Bot,
    request: Request,
    accepted: bool,
) -> None:
    await notify_admins_text(
        bot,
        price_decision_admin_text(request, accepted),
        admin_request_keyboard(request),
    )


async def notify_admins_canceled(
    bot: Bot,
    request: Request,
) -> None:
    await notify_admins_text(
        bot,
        "🚫 <b>Клієнт скасував заявку</b>\n\n"
        f"Заявка: <b>{request.number}</b>\n"
        f"Клієнт: {h(request.client_name)}",
        admin_request_keyboard(request),
    )


async def notify_admins_review(
    bot: Bot,
    request: Request,
    *,
    followup: bool = False,
) -> None:
    await notify_admins_text(
        bot,
        admin_review_notification(request, followup=followup),
    )
