# 🚀 DEPLOY — запуск канала «Тело просит» (для Президента)

Это **единственный ручной этап**. После него канал постит сам —
3 раза в день (08:00 / 14:00 / 21:00 МСК), при выключенном Mac, и сам пополняет банк.

## Сделать один раз (~10 минут)

1. **Канал.** Создай в Telegram публичный канал, выбери хендл (проект: `@telo_prosit_daily`).
2. **Бот-постер.** У **@BotFather** → `/newbot` → получи **BOT_TOKEN**.
   Добавь бота **администратором** канала с правом «Публиковать сообщения».
3. **Репозиторий.** Создай приватный репо `telo-prosit-bot` и залей туда содержимое
   папки `engine/` (именно её содержимое — `.github/` должен оказаться в корне репо):
   ```bash
   cd "telo_prosit_channel/engine" && git init && git add . && git commit -m "telo_prosit engine"
   git branch -M main
   git remote add origin https://github.com/<твой-аккаунт>/telo-prosit-bot.git
   git push -u origin main
   ```
4. **Секреты.** В репо → **Settings → Secrets and variables → Actions → New repository secret**:
   - `BOT_TOKEN` — токен из шага 2
   - `CHANNEL_ID` — `@telo_prosit_daily` (твой хендл) **или** числовой `-100…`
   - `ANTHROPIC_API_KEY` — ключ Anthropic (для автопополнения банка)
   - `FUNNEL_BOT_USERNAME` — *(необязательно)* username общего `funnel_bot` без `@`,
     чтобы в постах появлялась ссылка на лид-магнит с меткой `src=tpr`
5. **Проверка.** Вкладка **Actions → telo_prosit-post → Run workflow** (`count=1`).
   В канал должен упасть один пост. Дальше — по расписанию само.

## Наполнение банка

**Статус на 2026-07-18: в банке 36 готовых постов** (12 дней вещания по 3/день).
Проверить: `python3 post.py --status`. Дальше воркфлоу `telo_prosit-refill` держит
запас ≥ 20 сам. Если захочешь пополнять иначе — два пути, можно совмещать:

- **Руками (точнее).** Заполни эпизоды в `../launch/CONTENT_QUEUE.md` (убери метки 🔴),
  затем: `python3 fill_bank.py` — очередь превратится в посты.
- **Автоматом (быстрее).** Один раз: `python3 generate_posts.py --send --count 30`
  (нужен `ANTHROPIC_API_KEY`). Дальше воркфлоу `telo_prosit-refill` сам поддерживает
  запас ≥ 20 непоказанных постов.

## Локальные команды

```bash
python3 post.py               # dry-run: показать следующий пост, ничего не слать
python3 post.py --status      # что в банке
python3 post.py --send        # отправить (нужны BOT_TOKEN/CHANNEL_ID в .env или ENV)
```

> Секреты в коде отсутствуют. Локально — в файле `.env` рядом со скриптом
> (он в `.gitignore`), в облаке — только GitHub Secrets.
