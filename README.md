## Финансовый Telegram‑бот (трекинг расходов)

Бот на Python (aiogram + SQLite), поддерживает:

- **/add сумма категория** — добавить расход, например: `/add 199.90 еда`
- **/list** — последние 10 расходов
- **/stats** — статистика за 7 дней по категориям

### 1. Подготовка (локальный запуск на Windows)

- Установи Python 3.10+.
- В консоли в папке проекта выполни:

```bash
pip install -r requirements.txt
```

- Создай файл `.env` рядом с `main.py` и пропиши:

```bash
BOT_TOKEN=твой_токен_бота_от_BotFather
DATABASE_URL=sqlite+aiosqlite:///./finbot.db
PORT=8000
```

- Запусти бота локально (режим polling):

```bash
python main.py
```

Бот начнёт опрашивать Telegram и отвечать на команды.

### 2. Деплой на Render (webhook)

1. Залей этот проект в репозиторий (GitHub/GitLab).
2. На Render создай **Web Service**:
   - Connect repo → выбери репозиторий.
   - Environment: `Python`.
   - Build command: `pip install -r requirements.txt`
   - Start command: `python main.py`
3. В настройках Render задай переменные окружения:

- **BOT_TOKEN** — токен бота.
- **DATABASE_URL** — можно оставить `sqlite+aiosqlite:///./finbot.db` (или использовать PostgreSQL).
- **WEBHOOK_DOMAIN** — адрес сервиса Render, например: `https://my-finbot.onrender.com`
- **WEBHOOK_SECRET** — любая строка (секрет для проверки Telegram).
- **PORT** — Render сам передаёт порт в переменной `PORT`, можно не указывать вручную.

Когда Render поднимет сервис, бот автоматически выставит webhook и начнёт принимать сообщения через HTTPS.





### ???????? ????? ? ????????

- `/feedback <?????>` ? ?????????? ????????? ???????????? (?? ????????? ID 1485539422, ????? ?????? ????? `DEVELOPER_ID`).
- `/subscribe` ? ?????????? ?????? ? ??????? ?? ???????? (`SUBSCRIPTION_LINK`).

?????? ?????????? ?????????:

```
DEVELOPER_ID=1485539422
SUBSCRIPTION_LINK=https://t.me/your_channel
```
