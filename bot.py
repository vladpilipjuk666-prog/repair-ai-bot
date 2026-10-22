"""Точка входа.

Локально: long polling.
На Render (и любом хостинге с WEBHOOK_URL): webhook + health-check.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    ErrorEvent,
)

from config import (
    ADMIN_IDS,
    BOT_DESCRIPTION,
    BOT_SHORT_DESCRIPTION,
    BOT_TOKEN,
    LOG_LEVEL,
    PORT,
    WEBHOOK_PATH,
    WEBHOOK_SECRET,
    WEBHOOK_URL,
    validate_config,
)
from database import close_db, init_db
from handlers import admin, client, common, fallback

logger = logging.getLogger(__name__)

dp = Dispatcher(storage=MemoryStorage())
dp.include_router(common.router)
dp.include_router(admin.router)
dp.include_router(client.router)
dp.include_router(fallback.router)

USER_COMMANDS = [
    BotCommand(command="start", description="Головне меню"),
    BotCommand(command="new", description="Нова заявка"),
    BotCommand(command="my", description="Мої заявки"),
    BotCommand(command="prices", description="Орієнтовні ціни"),
    BotCommand(command="contacts", description="Контакти"),
    BotCommand(command="faq", description="Часті питання"),
    BotCommand(command="reviews", description="Відгуки клієнтів"),
    BotCommand(command="help", description="Як працює бот"),
    BotCommand(command="cancel", description="Скасувати заповнення"),
]

ADMIN_COMMANDS = [
    *USER_COMMANDS,
    BotCommand(command="admin", description="Адмін-панель"),
    BotCommand(command="stats", description="Статистика"),
    BotCommand(command="export", description="Експорт заявок CSV"),
]


@dp.errors()
async def error_handler(event: ErrorEvent) -> bool:
    logger.error(
        "Помилка при обробці update: %s",
        event.exception,
        exc_info=event.exception,
    )
    return True


async def setup_bot_profile(bot: Bot) -> None:
    """Обновляет описание и команды бота без BotFather."""
    try:
        await bot.set_my_short_description(
            short_description=BOT_SHORT_DESCRIPTION,
        )
        await bot.set_my_description(
            description=BOT_DESCRIPTION,
        )
        await bot.set_my_commands(
            USER_COMMANDS,
            scope=BotCommandScopeDefault(),
        )
        logger.info("Описание и команды бота обновлены")
    except Exception as error:
        logger.warning("Не удалось обновить профиль бота: %s", error)

    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(
                ADMIN_COMMANDS,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as error:
            logger.debug(
                "Не удалось установить админ-команды для %s: %s",
                admin_id,
                error,
            )


async def run_polling(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Режим: long polling")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


async def run_webhook(bot: Bot) -> None:
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler
    from aiohttp import web

    async def health(_request: web.Request) -> web.Response:
        return web.json_response(
            {
                "ok": True,
                "service": "repair-request-bot",
                "mode": "webhook",
            }
        )

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    webhook_endpoint = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_endpoint,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=False,
    )

    logger.info("Режим: webhook")
    logger.info("Webhook: %s", webhook_endpoint)
    logger.info("Health-check: %s/health", WEBHOOK_URL)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    validate_config()

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    await init_db()
    await setup_bot_profile(bot)

    try:
        if WEBHOOK_URL:
            await run_webhook(bot)
        else:
            await run_polling(bot)
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
