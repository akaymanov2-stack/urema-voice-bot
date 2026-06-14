# Деплой на Fly.io (always-on контейнер, long polling)

Бот едет как Docker-контейнер. Конфиг — в `Dockerfile` и `fly.toml`.
Секреты в образ **не попадают** — они задаются через `fly secrets` и читаются ботом
из переменных окружения (файл `.env` в контейнере не используется).

> ⚠️ Один токен — один polling. После деплоя на Fly **выключи локального бота** (Ctrl+C),
> иначе `TelegramConflictError`.

## 0. Установить flyctl и войти

```powershell
# Windows PowerShell
iwr https://fly.io/install.ps1 -useb | iex
fly auth signup   # или: fly auth login
```

## 1. Создать приложение (без деплоя)

Имя должно быть уникальным в Fly. Если `urema-voice-bot` занято — выбери другое
и поправь поле `app` в `fly.toml`.

```powershell
cd c:\Users\A\Desktop\urema-voice-bot
fly apps create urema-voice-bot
```

## 2. Создать том для кэша модели Whisper

```powershell
fly volumes create urema_data --region fra --size 3 --yes
```

## 3. Прописать секреты (значения возьми из своего .env)

```powershell
fly secrets set `
  TELEGRAM_BOT_TOKEN="..." `
  ALLOWED_USER_IDS="436160170" `
  CHANNEL_ID="-1003843142440" `
  SUPABASE_URL="https://obzetbngizlmkihjrxgx.supabase.co" `
  SUPABASE_SERVICE_ROLE_KEY="..." `
  BLOG_AUTHOR_IDENTIFIER="akaymanov@yandex.ru" `
  BLOG_AUTHOR_NAME="Andre de Kaymagne"
```

(`WHISPER_MODEL=small` и `HF_HOME` уже заданы в `fly.toml` → отдельно не нужны.
`SITE_URL`, `CHANNEL_MESSAGE`, формат даты берутся из дефолтов кода.)

## 4. Деплой

```powershell
fly deploy
fly scale count 1   # один экземпляр — чтобы не было двойного polling
```

## 5. Логи и управление

```powershell
fly logs                 # живые логи
fly status               # состояние машины
fly deploy               # повторный деплой после правок кода
fly secrets set KEY=...  # обновить секрет (вызовет рестарт)
```

Первый запуск скачает модель `small` в `/data` (на томе) — дальше старты быстрые.
Проверка: отправь боту голосовое → в логах `Черновик создан …`, в группе «Текст размещён».

## Заметки

- **RAM/модель.** `small` комфортна на 2 ГБ. Хочешь качество `medium` — подними память
  в `fly.toml` (`memory = "4gb"`) и поставь секрет `WHISPER_MODEL=medium`.
- **Стоимость.** Машина 2 ГБ работает 24/7 → тариф платный (несколько $/мес), как и на
  любой always-on платформе.
- **Railway/Render вместо Fly.** `Dockerfile` универсален: на Railway создаёшь сервис из
  репозитория, задаёшь те же переменные окружения, `fly.toml` игнорируется. На Render
  бери **Background Worker** (не Web Service — он засыпает).
