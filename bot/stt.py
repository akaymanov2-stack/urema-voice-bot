"""Распознавание речи через локальный faster-whisper.

Модель загружается лениво один раз и переиспользуется. Функция transcribe
блокирующая (CPU-bound) — вызывать из async-кода через asyncio.to_thread.
faster-whisper декодирует Telegram opus (.oga) напрямую, отдельный ffmpeg не нужен.
"""
import logging

from faster_whisper import WhisperModel

from .config import settings

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(
            "Загрузка модели Whisper: %s (%s / %s)",
            settings.whisper_model,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def transcribe(audio_path: str) -> str:
    """Возвращает распознанный текст (русский). Может вернуть пустую строку."""
    model = _get_model()
    segments, info = model.transcribe(audio_path, language=settings.whisper_language)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    logger.info("STT готово: %.1f c аудио → %d символов", info.duration, len(text))
    return text
