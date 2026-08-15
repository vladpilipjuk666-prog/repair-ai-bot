import base64
from typing import Optional

from openai import AsyncOpenAI

from config import OPENROUTER_API_KEY


# =========================================================
# OPENROUTER CLIENT
# =========================================================

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


# =========================================================
# MODEL
# =========================================================

TEXT_MODEL = "openrouter/free"


# =========================================================
# CHANNEL STYLES
# =========================================================

PC_REPAIR_STYLE = """
Ти пишеш для Telegram-каналу про ремонт
комп'ютерів, ноутбуків та іншої техніки.

Стиль:
- професійний;
- спокійний;
- сучасний;
- зрозумілий звичайній людині;
- без складного технічного жаргону;
- короткі абзаци;
- максимум конкретики;
- без нав'язливої реклами.

Показуй:

проблема → що зробили → результат.

Пост повинен читатися приблизно за
10–15 секунд.
"""


WEB_DEV_STYLE = """
Ти пишеш для Telegram-каналу про веб-розробку,
створення сайтів та цифрові рішення.

Стиль:
- сучасний;
- професійний;
- спокійний;
- простий для розуміння;
- без технічної води;
- короткі абзаци;
- акцент на користі для клієнта.

Показуй:

завдання → рішення → результат.

Пост повинен читатися приблизно за
10–15 секунд.
"""


# =========================================================
# BASE PROMPT
# =========================================================

BASE_PROMPT = """
Ти — AI-копірайтер професійного Telegram-каналу.

Твоя задача — перетворити сирий опис користувача
на короткий, красивий та зрозумілий пост.

Головне:

Людина повинна швидко:

1. зрозуміти проблему;
2. побачити, що було зроблено;
3. зрозуміти результат.

НЕ ПИШИ ДОВГО.

Не використовуй:

- воду;
- довгі вступи;
- банальні фрази;
- «ми раді повідомити»;
- «хочемо поділитися»;
- «як штучний інтелект»;
- надмірну рекламу;
- багато емодзі;
- багато хештегів.

Не вигадуй факти.

Якщо інформації немає —
не придумуй її.

Використовуй максимум 2–4 емодзі,
тільки якщо вони допомагають читанню.

Структура:

Короткий заголовок.

Проблема або завдання.

Що зробили.

Результат.

За необхідності — короткий заклик звернутися.

Текст повинен виглядати так,
ніби його написала реальна компанія,
а не шаблонний AI.

ПОВЕРТАЙ ТІЛЬКИ ГОТОВИЙ ТЕКСТ ПОСТА.
"""


# =========================================================
# HELPER
# =========================================================

async def chat(
    prompt: str,
    images: Optional[list[str]] = None,
) -> str:

    content = [
        {
            "type": "text",
            "text": prompt,
        }
    ]

    if images:

        for image_url in images:

            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    },
                }
            )

    response = await client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )

    result = response.choices[0].message.content

    if not result:
        raise RuntimeError(
            "AI не повернув текст."
        )

    return result.strip()


# =========================================================
# GENERATE POST
# =========================================================

async def generate_post(
    description: str,
    channel: str,
    image_descriptions: Optional[list[str]] = None,
) -> str:

    if channel == "PC REPAIR":

        style = PC_REPAIR_STYLE

    elif channel == "WEB DEV":

        style = WEB_DEV_STYLE

    else:

        style = ""


    image_context = ""

    if image_descriptions:

        image_context = """

Користувач також надав фотографії.

Інформація, отримана з фотографій:

""" + "\n\n".join(
            image_descriptions
        )


    prompt = f"""
{BASE_PROMPT}

{style}

Опис користувача:

{description}

{image_context}

Створи готовий Telegram-пост.

Одразу починай з тексту поста.
"""


    return await chat(prompt)


# =========================================================
# REGENERATE POST
# =========================================================

async def regenerate_post(
    description: str,
    channel: str,
    previous_post: str,
) -> str:

    if channel == "PC REPAIR":

        style = PC_REPAIR_STYLE

    else:

        style = WEB_DEV_STYLE


    prompt = f"""
{BASE_PROMPT}

{style}

Опис роботи:

{description}

Попередній варіант:

{previous_post}

Створи НОВИЙ варіант.

Не просто заміни кілька слів.

Зміни:

- подачу;
- структуру;
- формулювання;
- заголовок.

Але збережи головні факти.

Новий пост повинен бути коротким,
живим та природним.
"""


    return await chat(prompt)


# =========================================================
# EDIT POST
# =========================================================

async def edit_post(
    post: str,
    instruction: str,
) -> str:

    prompt = f"""
Ти — редактор Telegram-постів.

Поточний пост:

{post}

Побажання користувача:

{instruction}

Відредагуй пост відповідно до побажання.

Збережи всі факти.

Не додавай вигаданих деталей.

Зроби текст:

- коротким;
- красивим;
- природним;
- легким для читання.

ПОВЕРНИ ТІЛЬКИ ГОТОВИЙ ПОСТ.
"""


    return await chat(prompt)


# =========================================================
# ANALYZE IMAGE
# =========================================================

async def analyze_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> str:

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")


    image_url = (
        f"data:{mime_type};base64,{encoded}"
    )


    prompt = """
Проаналізуй фотографію для Telegram-поста.

Опиши тільки важливе:

- що зображено;
- стан техніки;
- що видно на фотографії;
- можливу проблему, якщо вона очевидна;
- що можна використати для опису роботи.

НЕ ВИГАДУЙ того, чого не видно.

Якщо щось неможливо визначити
з фотографії — так і скажи.

Відповідь повинна бути короткою.
"""


    return await chat(
        prompt,
        images=[image_url],
    )


# =========================================================
# ANALYZE MULTIPLE IMAGES
# =========================================================

async def analyze_images(
    images: list[tuple[bytes, str]],
) -> list[str]:

    results = []

    for image_bytes, mime_type in images:

        try:

            result = await analyze_image(
                image_bytes,
                mime_type,
            )

            results.append(result)

        except Exception as error:

            results.append(
                f"Фото не вдалося проаналізувати: {error}"
            )

    return results


# =========================================================
# IMAGE GENERATION
# =========================================================

async def generate_image(
    prompt: str,
) -> bytes:

    raise RuntimeError(
        "Безкоштовна генерація зображень "
        "через OpenRouter зараз недоступна. "
        "Функцію можна буде підключити окремо."
    )


# =========================================================
# IMAGE EDITING
# =========================================================

async def edit_image(
    image_bytes: bytes,
    instruction: str,
    mime_type: str = "image/jpeg",
) -> bytes:

    raise RuntimeError(
        "Безкоштовне AI-редагування зображень "
        "зараз не підключене. "
        "Текст та аналіз фотографій працюють "
        "через безкоштовний AI."
    )


# =========================================================
# BEFORE / AFTER
# =========================================================

async def create_before_after(
    before_image: bytes,
    after_image: bytes,
) -> bytes:

    raise RuntimeError(
        "AI-генерація зображення ДО / ПІСЛЯ "
        "потребує окремої image-моделі."
    )
