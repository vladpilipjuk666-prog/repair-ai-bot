"""Скачивание фото из Telegram и подготовка изображений для AI."""

from __future__ import annotations

import logging
from io import BytesIO

from aiogram import Bot
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


async def download_telegram_photo(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)
    if not file.file_path:
        raise RuntimeError("Telegram не вернул путь к файлу.")

    buffer = BytesIO()
    await bot.download_file(file.file_path, destination=buffer)
    return buffer.getvalue()


async def download_telegram_photos(
    bot: Bot,
    file_ids: list[str],
) -> list[bytes]:
    images: list[bytes] = []

    for file_id in file_ids:
        try:
            images.append(await download_telegram_photo(bot, file_id))
        except Exception as error:
            logger.warning("Не удалось скачать фото %s: %s", file_id, error)

    return images


def prepare_image_for_ai(
    data: bytes,
    max_side: int = 1280,
    quality: int = 85,
) -> bytes:
    """Уменьшает фото перед отправкой в AI.

    Это экономит токены и снижает риск превысить лимит запроса.
    Если Pillow не смог обработать файл, возвращаем оригинал.
    """
    try:
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)

            if image.mode not in {"RGB", "L"}:
                background = Image.new("RGB", image.size, "white")
                if image.mode in {"RGBA", "LA"}:
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")

            image.thumbnail((max_side, max_side))

            output = BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()
    except Exception as error:
        logger.warning("Не удалось подготовить фото для AI: %s", error)
        return data
