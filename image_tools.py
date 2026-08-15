from io import BytesIO
from typing import Optional

from aiogram import Bot


async def download_telegram_photo(
    bot: Bot,
    file_id: str,
) -> bytes:
    """
    Скачивает фотографию из Telegram
    и возвращает её как bytes.
    """

    file = await bot.get_file(file_id)

    buffer = BytesIO()

    await bot.download_file(
        file.file_path,
        destination=buffer,
    )

    return buffer.getvalue()


async def download_telegram_photos(
    bot: Bot,
    file_ids: list[str],
) -> list[bytes]:
    """
    Скачивает несколько фотографий из Telegram.
    """

    images = []

    for file_id in file_ids:

        try:

            image = await download_telegram_photo(
                bot,
                file_id,
            )

            images.append(image)

        except Exception as error:

            print(
                f"Не удалось скачать фото {file_id}: {error}"
            )

    return images


def get_mime_type(
    filename: Optional[str] = None,
) -> str:
    """
    Определяет MIME-тип изображения.
    """

    if not filename:
        return "image/jpeg"

    filename = filename.lower()

    if filename.endswith(".png"):
        return "image/png"

    if filename.endswith(".webp"):
        return "image/webp"

    if filename.endswith(".gif"):
        return "image/gif"

    return "image/jpeg"


def is_supported_image(
    filename: Optional[str],
) -> bool:
    """
    Проверяет, является ли файл
    поддерживаемым изображением.
    """

    if not filename:
        return False

    filename = filename.lower()

    supported = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    )

    return filename.endswith(supported)


def limit_images(
    file_ids: list[str],
    maximum: int = 10,
) -> list[str]:
    """
    Ограничивает количество фотографий.
    """

    return file_ids[:maximum]
