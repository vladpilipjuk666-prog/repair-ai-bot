import os

from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# TELEGRAM
# =========================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)


# =========================================================
# OPENROUTER
# =========================================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)


# =========================================================
# TELEGRAM CHANNELS
# =========================================================

PC_REPAIR_CHANNEL_ID = os.getenv(
    "PC_REPAIR_CHANNEL_ID"
)

WEB_DEV_CHANNEL_ID = os.getenv(
    "WEB_DEV_CHANNEL_ID"
)


# =========================================================
# OWNER
# =========================================================

OWNER_ID = os.getenv(
    "OWNER_ID"
)


# =========================================================
# VALIDATION
# =========================================================

def validate_config():

    missing = []


    # Telegram

    if not TELEGRAM_BOT_TOKEN:

        missing.append(
            "TELEGRAM_BOT_TOKEN"
        )


    # OpenRouter

    if not OPENROUTER_API_KEY:

        missing.append(
            "OPENROUTER_API_KEY"
        )


    # PC Repair channel

    if not PC_REPAIR_CHANNEL_ID:

        missing.append(
            "PC_REPAIR_CHANNEL_ID"
        )


    # Web Dev channel

    if not WEB_DEV_CHANNEL_ID:

        missing.append(
            "WEB_DEV_CHANNEL_ID"
        )


    if missing:

        raise RuntimeError(
            "Не вистачає змінних середовища: "
            + ", ".join(missing)
        )
