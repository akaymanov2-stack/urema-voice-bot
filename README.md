# uRema Voice Bot

Telegram-бот: голосовое сообщение → черновик поста в блоге **uRema** (Next.js + Supabase) + уведомление в канал.

## Что делает

1. Принимает голосовое сообщение (только от разрешённых `user_id`).
2. Распознаёт речь локально через **faster-whisper** (русский, без облака).
3. Создаёт в Supabase черновик поста:
   - заголовок = текущая дата (`ДД.ММ.ГГГГ`),
   - тело = расшифровка,
   - категория = `uRema` (создаётся автоматически, если нет),
   - картинка = заранее загруженный плейсхолдер (грузится один раз и переиспользуется),
   - статус = `draft`.
4. Присылает в личку ссылку на редактирование: `/<site>/admin/panel/posts/<id>`.
5. Публикует в канал uRema сообщение «Текст размещён».

> ⚠️ Черновик не имеет публичной страницы (она появляется только после публикации статуса `published`), поэтому в канал уходит сообщение **без ссылки**. Рабочая ссылка на редактирование приходит вам в личку.

## Архитектура

```
bot/
  config.py     # настройки из .env (pydantic-settings)
  stt.py        # faster-whisper
  blog.py       # Supabase: категория, плейсхолдер, черновик
  handlers.py   # хэндлеры aiogram + whitelist
  main.py       # запуск long polling
assets/
  placeholder.png   # ваша картинка-заглушка (положить вручную)
```

Бот пишет в БД блога **напрямую** через `service_role` ключ — он не зависит от того, поднят ли сайт.

## Установка

```bash
cd urema-voice-bot
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # затем заполнить .env
```

Положите картинку-заглушку в `assets/placeholder.png` (любой PNG/JPG; путь меняется через `PLACEHOLDER_PATH`).

> ffmpeg отдельно ставить не нужно — faster-whisper декодирует Telegram opus сам (через PyAV). Если на вашей платформе декодирование не заработает, поставьте системный ffmpeg.

## Где взять токены и доступы

| Переменная | Где взять |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `ALLOWED_USER_IDS` | ваш Telegram user_id у [@userinfobot](https://t.me/userinfobot) |
| `CHANNEL_ID` | `@username` канала (или числовой `-100...`). **Добавьте бота администратором канала** с правом публикации |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → **service_role** (секрет, полный доступ к БД!) |
| `BLOG_AUTHOR_IDENTIFIER` | (опц.) `identifier` из таблицы `users`, чтобы проставить автора поста |

## Запуск

```bash
python -m bot.main
```

## Как протестировать

1. Запустите бота, напишите ему `/start` — должно прийти приветствие.
2. Отправьте голосовое. Бот по шагам отчитается: получил → распознаю → создаю черновик → ✅ + ссылка.
3. Откройте ссылку — черновик в админке с датой, категорией uRema и картинкой-заглушкой.
4. В канале появится «Текст размещён».
5. Любая ошибка приходит вам сообщением (а не «молча»), детали — в логах консоли.

## Деплой на VPS (long polling, 24/7)

systemd-юнит `/etc/systemd/system/urema-bot.service`:

```ini
[Unit]
Description=uRema Voice Bot
After=network-online.target

[Service]
WorkingDirectory=/opt/urema-voice-bot
ExecStart=/opt/urema-voice-bot/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now urema-bot
sudo journalctl -u urema-bot -f   # логи
```

> Первый запуск скачает модель Whisper (`medium` ≈ 1.5 ГБ). Для слабого CPU поставьте `WHISPER_MODEL=small`; при наличии GPU — `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16`, `WHISPER_MODEL=large-v3`.

## Кэш

`.bot_cache.json` хранит id категории, URL плейсхолдера и author_id, чтобы не дёргать API при каждом посте. Удалите файл, если поменяли категорию/заглушку.
