import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Telegram channels
PC_REPAIR_CHANNEL_ID = os.getenv("PC_REPAIR_CHANNEL_ID")
WEB_DEV_CHANNEL_ID = os.getenv("WEB_DEV_CHANNEL_ID")

# Owner
OWNER_ID = os.getenv("OWNER_ID")


def validate_config():
    missing = []

    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if missing:
        raise RuntimeError(
            "Не вистачає змінних: " + ", ".join(missing)
        )
