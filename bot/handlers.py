"""Telegram-хэндлеры: оркестрация всего сценария и whitelist по user_id.

Порядок шагов и обработка ошибок: каждый шаг изолирован. Если падает публикация
в канал — черновик уже сохранён, пользователь получает и ссылку, и предупреждение.
"""
import asyncio
import logging
import tempfile
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from . import blog, stt
from .config import settings

logger = logging.getLogger(__name__)
router = Router()


def _allowed(message: Message) -> bool:
    return bool(message.from_user) and message.from_user.id in settings.allowed_ids


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if not _allowed(message):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    await message.answer(
        "Привет! Пришлите голосовое сообщение — я расшифрую его "
        "и создам черновик в блоге uRema."
    )


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    if not _allowed(message):
        logger.warning("Отклонён неразрешённый пользователь: %s", message.from_user.id)
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return

    status = await message.answer("🎧 Получил голосовое, обрабатываю…")

    # 1 + 2. Скачивание и распознавание
    try:
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / f"{message.voice.file_id}.oga"
            await message.bot.download(message.voice, destination=audio_path)
            logger.info(
                "Аудио скачано: %d Б, %d c",
                message.voice.file_size or 0,
                message.voice.duration or 0,
            )

            await status.edit_text("📝 Распознаю речь…")
            text = await asyncio.to_thread(stt.transcribe, str(audio_path))
    except Exception:
        logger.exception("Ошибка скачивания/распознавания")
        await status.edit_text(
            "❌ Не удалось скачать или распознать аудио. Подробности в логах."
        )
        return

    if not text:
        await status.edit_text(
            "⚠️ Речь не распознана (пустой результат). Попробуйте ещё раз."
        )
        return

    # 3. Создание черновика
    await status.edit_text("🗂 Создаю черновик в блоге…")
    try:
        post = await asyncio.to_thread(blog.create_draft, text)
    except Exception:
        logger.exception("Ошибка создания черновика")
        await status.edit_text(
            "❌ Текст распознан, но не удалось создать черновик в блоге. "
            "Подробности в логах."
        )
        return

    link = blog.edit_link(post["id"])
    await status.edit_text(
        f"✅ Черновик создан: <b>{post['title']}</b>\n🔗 Редактировать: {link}"
    )

    # 4. Уведомление в канал (нефатально для черновика)
    try:
        await message.bot.send_message(settings.channel_id, settings.channel_message)
        logger.info("Уведомление отправлено в канал %s", settings.channel_id)
    except Exception:
        logger.exception("Ошибка отправки в канал")
        await message.answer(
            "⚠️ Черновик сохранён, но не получилось опубликовать сообщение в канал. "
            "Проверьте, что бот добавлен администратором канала."
        )


@router.message()
async def handle_other(message: Message) -> None:
    if not _allowed(message):
        return
    await message.answer("Пришлите голосовое сообщение 🎙")
