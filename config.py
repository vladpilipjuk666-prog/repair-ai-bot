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
# OPENAI
# =========================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
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

    if not TELEGRAM_BOT_TOKEN:
        missing.append(
            "TELEGRAM_BOT_TOKEN"
        )

    if not OPENAI_API_KEY:
        missing.append(
            "OPENAI_API_KEY"
        )

    if not PC_REPAIR_CHANNEL_ID:
        missing.append(
            "PC_REPAIR_CHANNEL_ID"
        )

    if not WEB_DEV_CHANNEL_ID:
        missing.append(
            "WEB_DEV_CHANNEL_ID"
        )

    if missing:

        raise RuntimeError(
            "Не вистачає змінних середовища: "
            + ", ".join(missing)
        )
