import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot_config import get_settings
from db import add_expense, init_db, list_expenses, stats_by_period


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    text = (
        "Привет! Я финансовый трекер 💰\n\n"
        "Я помогу записывать расходы и смотреть статистику.\n\n"
        "Основные команды:\n"
        "• /add сумма категория — добавить расход (пример: /add 250 еда)\n"
        "• /list — последние расходы\n"
        "• /stats — статистика за 7 дней по категориям\n"
    )
    await message.answer(text)


def parse_add_args(args: Optional[str]) -> tuple[float, str] | None:
    if not args:
        return None
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return None
    amount_str, category = parts
    try:
        amount = float(amount_str.replace(",", "."))
    except ValueError:
        return None
    category = category.strip().lower()
    if not category:
        return None
    return amount, category


@router.message(Command("add"))
async def cmd_add(message: types.Message, command: CommandObject) -> None:
    parsed = parse_add_args(command.args)
    if not parsed:
        await message.answer(
            "Неверный формат.\n"
            "Используй: <code>/add сумма категория</code>\n"
            "Пример: <code>/add 199.90 еда</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    amount, category = parsed
    user_id = message.from_user.id
    await add_expense(user_id=user_id, amount=amount, category=category)
    await message.answer(f"Добавил расход: {amount:.2f} ₽, категория: {category}")


@router.message(Command("list"))
async def cmd_list(message: types.Message) -> None:
    user_id = message.from_user.id
    expenses = await list_expenses(user_id=user_id, limit=10)
    if not expenses:
        await message.answer("Пока нет записанных расходов.")
        return

    lines = []
    for e in expenses:
        created = e.created_at.strftime("%d.%m %H:%M") if e.created_at else ""
        lines.append(f"{created} — {e.amount:.2f} ₽ [{e.category}]")

    text = "Последние расходы:\n\n" + "\n".join(lines)
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    user_id = message.from_user.id
    stats = await stats_by_period(user_id=user_id, days=7)
    if not stats:
        await message.answer("За последние 7 дней расходов ещё нет.")
        return

    total = sum(stats.values())
    lines = []
    for cat, amount in stats.items():
        percent = amount / total * 100 if total else 0
        lines.append(f"{cat}: {amount:.2f} ₽ ({percent:.1f}%)")

    text = "Статистика за 7 дней:\n\n" + "\n".join(lines) + f"\n\nВсего: {total:.2f} ₽"
    await message.answer(text)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="О боте и список команд"),
        BotCommand(command="add", description="Добавить расход /add сумма категория"),
        BotCommand(command="list", description="Показать последние расходы"),
        BotCommand(command="stats", description="Статистика за 7 дней"),
    ]
    await bot.set_my_commands(commands)


async def run_polling() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения.")

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)

    await init_db()
    await set_bot_commands(bot)

    logger.info("Запускаю бота в режиме polling (локальная разработка)...")
    await dp.start_polling(bot)


async def run_webhook() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения.")
    if not settings.webhook_domain:
        raise RuntimeError("WEBHOOK_DOMAIN не задан для режима webhook.")

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)

    await init_db()
    await set_bot_commands(bot)

    app = web.Application()
    webhook_path = f"/webhook/{settings.bot_token}"
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    setup_application(app, dp)

    webhook_url = settings.webhook_domain.rstrip("/") + webhook_path
    await bot.set_webhook(url=webhook_url, secret_token=settings.webhook_secret)
    logger.info("Webhook установлен: %s", webhook_url)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    logger.info("Сервер слушает порт %s", settings.port)
    await site.start()

    # держим процесс живым
    while True:
        await asyncio.sleep(3600)


async def main() -> None:
    if settings.webhook_domain:
        await run_webhook()
    else:
        await run_polling()


if __name__ == "__main__":
    asyncio.run(main())


