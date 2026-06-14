# Деплой на Linux VPS (systemd, long polling)

Бот работает 24/7 как systemd-сервис. ffmpeg ставить не нужно — faster-whisper
декодирует аудио через встроенный PyAV.

> ⚠️ Один токен — один polling. Перед запуском на VPS **остановите локального бота**
> (Ctrl+C), иначе будет `TelegramConflictError: terminated by other getUpdates request`.

Дальше `you@local` — команды на вашей машине, `vps$` — на сервере по SSH.
Подставьте свои значения: `VPS_USER`, `VPS_HOST`.

## 1. Зависимости на сервере (Ubuntu/Debian)

```bash
vps$ sudo apt update
vps$ sudo apt install -y python3 python3-venv python3-pip rsync
vps$ python3 --version    # нужен 3.11+
```
(Для RHEL/Alma/Rocky: `sudo dnf install -y python3 python3-pip rsync`.)

## 2. Скопировать проект на сервер

`tar` и `scp` есть в Windows PowerShell из коробки — этого достаточно, rsync не нужен.
Каталог назначения — `/opt/urema-voice-bot`.

```powershell
# На локальной машине (PowerShell): архив БЕЗ venv/кэша/мусора, но С .env и плейсхолдером
you@local> tar --exclude=.venv --exclude=__pycache__ --exclude=.bot_cache.json `
  -czf urema-bot.tgz -C C:\Users\A\Desktop urema-voice-bot
you@local> scp urema-bot.tgz VPS_USER@VPS_HOST:/tmp/
```

```bash
# На сервере: распаковать в /opt и стать владельцем
vps$ sudo mkdir -p /opt && sudo tar xzf /tmp/urema-bot.tgz -C /opt
vps$ sudo chown -R $USER /opt/urema-voice-bot && rm /tmp/urema-bot.tgz
```

> Альтернатива, если есть rsync: `rsync -av --delete --exclude '.venv' --exclude '__pycache__' --exclude '.bot_cache.json' -e ssh /c/Users/A/Desktop/urema-voice-bot/ VPS_USER@VPS_HOST:/opt/urema-voice-bot/`

`.env` со всеми секретами уезжает вместе с архивом.
Убедитесь, что на сервере `/opt/urema-voice-bot/.env` и `assets/placeholder.png` на месте:

```bash
vps$ ls -la /opt/urema-voice-bot/.env /opt/urema-voice-bot/assets/placeholder.png
vps$ chmod 600 /opt/urema-voice-bot/.env    # секреты только владельцу
```

## 3. Виртуальное окружение и зависимости

```bash
vps$ cd /opt/urema-voice-bot
vps$ python3 -m venv .venv
vps$ .venv/bin/pip install -U pip
vps$ .venv/bin/pip install -r requirements.txt
```

## 4. Пробный запуск (скачает модель Whisper один раз)

```bash
vps$ cd /opt/urema-voice-bot && .venv/bin/python -m bot.main
```
Отправьте боту голосовое. Дождитесь «Черновик создан …», затем Ctrl+C.
Модель кэшируется в `~/.cache/huggingface`, повторно не качается.

> Если на VPS < 2 ГБ RAM, `medium` может упасть по памяти. Поставьте в `.env`
> `WHISPER_MODEL=small` (≈0.5 ГБ) и перезапустите.

## 5. Установить systemd-сервис

```bash
vps$ sudo cp /opt/urema-voice-bot/deploy/urema-bot.service /etc/systemd/system/urema-bot.service
vps$ sudo sed -i "s/__USER__/$USER/" /etc/systemd/system/urema-bot.service
vps$ sudo systemctl daemon-reload
vps$ sudo systemctl enable --now urema-bot
```

## 6. Управление и логи

```bash
vps$ systemctl status urema-bot        # состояние
vps$ journalctl -u urema-bot -f        # живые логи
vps$ sudo systemctl restart urema-bot  # перезапуск
vps$ sudo systemctl stop urema-bot     # остановить
```

## Обновление кода в будущем

```powershell
you@local> tar --exclude=.venv --exclude=__pycache__ --exclude=.bot_cache.json `
  -czf urema-bot.tgz -C C:\Users\A\Desktop urema-voice-bot
you@local> scp urema-bot.tgz VPS_USER@VPS_HOST:/tmp/
```
```bash
vps$ sudo tar xzf /tmp/urema-bot.tgz -C /opt && sudo chown -R $USER /opt/urema-voice-bot && rm /tmp/urema-bot.tgz
vps$ cd /opt/urema-voice-bot && .venv/bin/pip install -r requirements.txt   # если менялись зависимости
vps$ sudo systemctl restart urema-bot
```
