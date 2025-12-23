import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    bot_token: str
    db_url: str
    developer_id: int | None
    subscription_link: str | None
    webhook_domain: str | None
    webhook_secret: str | None
    port: int


def get_settings() -> Settings:
    raw_port = os.getenv("PORT", "") or "8000"
    try:
        port = int(raw_port)
    except ValueError:
        port = 8000

    raw_dev_id = os.getenv("DEVELOPER_ID", "").strip()
    developer_id: int | None
    try:
        developer_id = int(raw_dev_id) if raw_dev_id else 1485539422
    except ValueError:
        developer_id = 1485539422

    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        db_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./finbot.db"),
        developer_id=developer_id,
        subscription_link=os.getenv("SUBSCRIPTION_LINK"),
        webhook_domain=os.getenv("WEBHOOK_DOMAIN"),
        webhook_secret=os.getenv("WEBHOOK_SECRET"),
        port=port,
    )

