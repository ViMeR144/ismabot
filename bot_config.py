import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    bot_token: str
    db_url: str
    webhook_domain: str | None
    webhook_secret: str | None
    port: int


def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        db_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./finbot.db"),
        webhook_domain=os.getenv("WEBHOOK_DOMAIN"),
        webhook_secret=os.getenv("WEBHOOK_SECRET"),
        port=int(os.getenv("PORT", "8000")),
    )


