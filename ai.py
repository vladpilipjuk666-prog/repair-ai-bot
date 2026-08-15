import base64
from typing import Optional

from openai import AsyncOpenAI

from config import OPENAI_API_KEY


# =========================================================
# OPENAI CLIENT
# =========================================================

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)


# =========================================================
# МОДЕЛІ
# =========================================================

TEXT_MODEL = "gpt-5.6"
IMAGE_MODEL = "gpt-image-2"


# =========================================================
# СТИЛІ КАНАЛІВ
# =========================================================

PC_REPAIR_STYLE = """
Ти пишеш для Telegram-каналу про ремонт комп'ютерів,
ноутбуків та іншої техніки.

Стиль:
- професійний;
- спокійний;
- сучасний;
- зрозумілий звичайній людині;
- без складного технічного жаргону;
- короткі абзаци;
- максимум конкретики;
- без зайвої реклами.

Показуй:
проблему → що зробили → результат.

Пост повинен читатися приблизно за 10–15 секунд.
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

Пост повинен читатися приблизно за 10–15 секунд.
"""


# =========================================================
# ЗАГАЛЬНИЙ ПРОМПТ
# =========================================================

BASE_PROMPT = """
Ти — AI-копірайтер професійного Telegram-каналу.

Твоя головна задача — перетворити сирий опис користувача
на короткий, красивий та зрозумілий пост.

ВАЖЛИВО:

Не пиши довго.

Людина повинна:
1. швидко зрозуміти проблему;
2. побачити, що було зроблено;
3. зрозуміти результат.

Не використовуй:
- воду;
- довгі вступи;
- банальні фрази;
- "ми раді повідомити";
- "хочемо поділитися";
- "як штучний інтелект";
- надмірну рекламу;
- багато емодзі;
- багато хештегів.

Не вигадуй факти.

Якщо певної інформації немає —
не придумуй її.

Використовуй максимум 2–4 емодзі,
і тільки якщо вони реально допомагають читанню.

Структура:

Короткий заголовок

Короткий опис проблеми або завдання.

Що зробили.

Результат.

За необхідності — короткий заклик звернутися.

Текст повинен виглядати так,
ніби його написала реальна компанія,
а не шаблонний AI.
"""


# =========================================================
# СТВОРЕННЯ ПОСТА
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

Ось інформація, отримана з фотографій:

""" + "\n\n".join(image_descriptions)

    prompt = f"""
{BASE_PROMPT}

{style}

Опис користувача:

{description}

{image_context}

Створи готовий Telegram-пост.
Одразу починай з тексту поста.
"""


    response = await client.responses.create(
        model=TEXT_MODEL,
        input=prompt,
    )

    return response.output_text.strip()


# =========================================================
# ПЕРЕРОБКА ПОСТА
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

Попередній варіант поста:

{previous_post}

Створи НОВИЙ варіант.

Не просто заміни декілька слів.

Зміни:
- подачу;
- структуру;
- формулювання;
- заголовок.

Але залиш головну інформацію.

Новий пост повинен бути коротким,
живим та природним.
"""


    response = await client.responses.create(
        model=TEXT_MODEL,
        input=prompt,
    )

    return response.output_text.strip()


# =========================================================
# РЕДАГУВАННЯ ПОСТА ЗА КОМАНДОЮ
# =========================================================

async def edit_post(
    post: str,
    instruction: str,
) -> str:

    prompt = f"""
Ти — редактор Telegram-постів.

Ось поточний пост:

{post}

Користувач хоче:

{instruction}

Відредагуй пост відповідно до побажання.

Збережи факти.

Не додавай вигаданих деталей.

Зроби текст:
- коротким;
- красивим;
- природним;
- легким для читання.

Поверни тільки готовий пост.
"""


    response = await client.responses.create(
        model=TEXT_MODEL,
        input=prompt,
    )

    return response.output_text.strip()


# =========================================================
# АНАЛІЗ ФОТО
# =========================================================

async def analyze_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> str:

    encoded = base64.b64encode(image_bytes).decode("utf-8")

    image_url = (
        f"data:{mime_type};base64,{encoded}"
    )

    response = await client.responses.create(
        model=TEXT_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": """
Проаналізуй це фото для Telegram-поста.

Опиши тільки важливі речі:
- що зображено;
- який стан техніки;
- що могло бути проблемою;
- що можна використати для опису роботи.

Не вигадуй того, чого не видно.
""",
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url,
                    },
                ],
            }
        ],
    )

    return response.output_text.strip()


# =========================================================
# АНАЛІЗ КІЛЬКОХ ФОТО
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
# ГЕНЕРАЦІЯ ЗОБРАЖЕННЯ
# =========================================================

async def generate_image(
    prompt: str,
) -> bytes:

    response = await client.responses.create(
        model=TEXT_MODEL,
        input=prompt,
        tools=[
            {
                "type": "image_generation"
            }
        ],
    )

    for output in response.output:

        if output.type == "image_generation_call":

            return base64.b64decode(
                output.result
            )

    raise RuntimeError(
        "AI не повернув зображення."
    )


# =========================================================
# AI-РЕДАГУВАННЯ ЗОБРАЖЕННЯ
# =========================================================

async def edit_image(
    image_bytes: bytes,
    instruction: str,
    mime_type: str = "image/jpeg",
) -> bytes:

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    image_url = (
        f"data:{mime_type};base64,{encoded}"
    )

    prompt = f"""
Відредагуй це зображення.

Інструкція користувача:

{instruction}

ВАЖЛИВО:

Збережи головний об'єкт фотографії.

Не змінюй його без необхідності.

Редагуй тільки те,
що попросив користувач.

Зображення повинно залишатися
реалістичним та природним.
"""


    response = await client.responses.create(
        model=TEXT_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url,
                    },
                ],
            }
        ],
        tools=[
            {
                "type": "image_generation"
            }
        ],
    )

    for output in response.output:

        if output.type == "image_generation_call":

            return base64.b64decode(
                output.result
            )

    raise RuntimeError(
        "AI не повернув відредаговане зображення."
    )


# =========================================================
# СТВОРЕННЯ "ДО / ПІСЛЯ"
# =========================================================

async def create_before_after(
    before_image: bytes,
    after_image: bytes,
) -> bytes:

    before_encoded = base64.b64encode(
        before_image
    ).decode("utf-8")

    after_encoded = base64.b64encode(
        after_image
    ).decode("utf-8")

    before_url = (
        f"data:image/jpeg;base64,{before_encoded}"
    )

    after_url = (
        f"data:image/jpeg;base64,{after_encoded}"
    )

    prompt = """
Створи професійне зображення
"ДО / ПІСЛЯ" для Telegram-публікації.

Використай дві фотографії:

Перша — стан ДО.

Друга — стан ПІСЛЯ.

Зроби акуратну композицію,
де обидва зображення добре видно.

Додай прості підписи:

ДО

ПІСЛЯ

Не змінюй саму техніку
і не вигадуй нових деталей.

Основна мета — чітко показати
різницю між двома фотографіями.
"""


    response = await client.responses.create(
        model=TEXT_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                    {
                        "type": "input_image",
                        "image_url": before_url,
                    },
                    {
                        "type": "input_image",
                        "image_url": after_url,
                    },
                ],
            }
        ],
        tools=[
            {
                "type": "image_generation"
            }
        ],
    )

    for output in response.output:

        if output.type == "image_generation_call":

            return base64.b64decode(
                output.result
            )

    raise RuntimeError(
        "Не вдалося створити зображення ДО / ПІСЛЯ."
    )
