import datetime as dt
import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery, BufferedInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot_config import get_settings
from db import init_db, has_active_subscription, set_subscription
from finance_service import (
    get_recent_expenses,
    get_week_stats,
    record_expense,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = Router()


async def ensure_subscription(message: types.Message) -> bool:
    user_id = message.from_user.id
    if await has_active_subscription(user_id):
        return True
    await message.answer("Нужна активная подписка. Оформите через /subscribe.")
    return False


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    text = (
        "Привет! Это бот для учёта расходов.

Основные команды:
• /add сумма категория — добавить трату (пример: /add 250 еда)
• /list — последние 10 трат
• /stats — статистика за 7 дней
• /monthstats — статистика за 30 дней (подписка)
• /export — экспорт последних трат в CSV (подписка)
• /feedback текст — написать разработчику
• /subscribe — оформить подписку
"
    )
    await message.answer(text)


@router.message(Command("add"))
async def cmd_add(message: types.Message, command: CommandObject) -> None:
    parsed = parse_add_args(command.args)
    if not parsed:
        await message.answer(
            "Неверный формат.
Используйте: <code>/add сумма категория</code>
Пример: <code>/add 199.90 еда</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    amount, category = parsed
    user_id = message.from_user.id
    await record_expense(user_id=user_id, amount=amount, category=category)
    await message.answer(f"Записал трату: {amount:.2f} руб., категория: {category}")


@router.message(Command("list"))
async def cmd_list(message: types.Message) -> None:
    user_id = message.from_user.id
    expenses = await get_recent_expenses(user_id=user_id, limit=10)
    if not expenses:
        await message.answer("Трат пока нет.")
        return

    lines = []
    for e in expenses:
        created = e.created_at.strftime("%d.%m %H:%M") if e.created_at else ""
        lines.append(f"{created} ? {e.amount:.2f} руб. [{e.category}]")

    text = "Последние расходы:

" + "
".join(lines)
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    user_id = message.from_user.id
    stats = await get_week_stats(user_id=user_id, days=7)
    if not stats:
        await message.answer("За 7 дней трат не найдено.")
        return

    total = sum(stats.values())
    lines = []
    for cat, amount in stats.items():
        percent = amount / total * 100 if total else 0
        lines.append(f"{cat}: {amount:.2f} руб. ({percent:.1f}%)")

    text = "Статистика за 7 дней:

" + "
".join(lines) + f"

Итого: {total:.2f} руб."
    await message.answer(text)


@router.message(Command("feedback"))
async def cmd_feedback(message: types.Message, command: CommandObject) -> None:
    feedback_text = (command.args or "").strip()
    if not feedback_text:
        await message.answer("Напишите текст после команды: /feedback ваш вопрос или предложение.")
        return

    developer_id = settings.developer_id
    if not developer_id:
        await message.answer("Получатель обратной связи не настроен. Свяжитесь с разработчиком напрямую.")
        return

    user = message.from_user
    sender = f"{user.full_name or ''} (@{user.username}) id={user.id}"
    body = (
        "Новое сообщение обратной связи
"
        f"От: {sender}
"
        f"Текст:
{feedback_text}"
    )
    await message.bot.send_message(chat_id=developer_id, text=body)
    await message.answer("Сообщение отправлено разработчику. Спасибо за обратную связь!")


@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message) -> None:
    if settings.payment_provider_token:
        price_kop = int(settings.subscription_price) * 100
        prices = [LabeledPrice(label=f"Подписка на {settings.subscription_days} дней", amount=price_kop)]
        await message.answer_invoice(
            title="Подписка",
            description=f"Подписка на {settings.subscription_days} дней",
            provider_token=settings.payment_provider_token,
            currency=settings.subscription_currency,
            prices=prices,
            payload="subscription",
        )
        return

    link = (settings.subscription_link or "").strip()
    if not link:
        await message.answer("Ссылка на подписку не настроена. Установите SUBSCRIPTION_LINK.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Перейти к подписке", url=link)]]
    )
    await message.answer("Оформить подписку можно по кнопке ниже:", reply_markup=kb)


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message) -> None:
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=settings.subscription_days)
    await set_subscription(user_id=message.from_user.id, expires_at=expires_at)
    await message.answer(
        f"Подписка активирована до {expires_at:%d.%m.%Y}. Спасибо за поддержку!"
    )


@router.message(Command("monthstats"))
async def cmd_month_stats(message: types.Message) -> None:
    if not await ensure_subscription(message):
        return
    user_id = message.from_user.id
    stats = await get_week_stats(user_id=user_id, days=30)
    if not stats:
        await message.answer("За последние 30 дней трат не найдено.")
        return

    total = sum(stats.values())
    lines = []
    for cat, amount in stats.items():
        percent = amount / total * 100 if total else 0
        lines.append(f"{cat}: {amount:.2f} руб. ({percent:.1f}%)")

    text = "Статистика за 30 дней:

" + "
".join(lines) + f"

Итого: {total:.2f} руб."
    await message.answer(text)


@router.message(Command("export"))
async def cmd_export(message: types.Message) -> None:
    if not await ensure_subscription(message):
        return
    user_id = message.from_user.id
    expenses = await get_recent_expenses(user_id=user_id, limit=100)
    if not expenses:
        await message.answer("Нет расходов для экспорта.")
        return

    rows = ["date,amount,category"]
    for e in expenses:
        date_str = e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else ""
        rows.append(f"{date_str},{e.amount:.2f},{e.category}")

    csv_data = "
".join(rows).encode("utf-8")
    file = BufferedInputFile(csv_data, filename="expenses.csv")
    await message.answer_document(document=file, caption="Последние операции (CSV)")


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Старт и помощь"),
        BotCommand(command="add", description="Добавить трату"),
        BotCommand(command="list", description="Последние траты"),
        BotCommand(command="stats", description="Статистика 7 дней"),
        BotCommand(command="feedback", description="Написать разработчику"),
        BotCommand(command="subscribe", description="Оформить подписку"),
        BotCommand(command="monthstats", description="Статистика 30 дней (подписка)"),
        BotCommand(command="export", description="Экспорт CSV (подписка)"),
    ]
    await bot.set_my_commands(commands)


async def run_polling() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    await init_db()
    await set_bot_commands(bot)

    logger.info("Starting bot in polling mode (local development)...")
    await dp.start_polling(bot)


async def run_webhook() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    if not settings.webhook_domain:
        raise RuntimeError("WEBHOOK_DOMAIN is not configured")

    bot = Bot(token=settings.bot_token)
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
    logger.info("Webhook set to %s", webhook_url)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    logger.info("Listening on port %s", settings.port)
    await site.start()

    while True:
        await asyncio.sleep(3600)


async def main() -> None:
    if settings.webhook_domain:
        await run_webhook()
    else:
        await run_polling()


if __name__ == "__main__":
    asyncio.run(main())
