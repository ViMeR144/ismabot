"""
Сервисный слой для работы с финансами.

Здесь инкапсулируется бизнес-логика поверх БД:
- запись расхода;
- получение последних расходов;
- агрегированная статистика по периодам.
"""

from __future__ import annotations

from typing import Iterable

from db import Expense, add_expense, list_expenses, stats_by_period


async def record_expense(user_id: int, amount: float, category: str) -> Expense:
    """
    Добавляет расход пользователя.

    Здесь можно будет легко добавить:
    - валидацию категорий;
    - ограничения/лимиты;
    - доп. побочные эффекты (логирование, нотификации).
    """
    normalized_category = category.strip().lower()
    return await add_expense(user_id=user_id, amount=amount, category=normalized_category)


async def get_recent_expenses(user_id: int, limit: int = 10) -> Iterable[Expense]:
    """Возвращает последние расходы пользователя."""
    return await list_expenses(user_id=user_id, limit=limit)


async def get_week_stats(user_id: int, days: int = 7) -> dict[str, float]:
    """Агрегированная статистика расходов по категориям за указанный период."""
    return await stats_by_period(user_id=user_id, days=days)



