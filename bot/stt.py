"""Распознавание речи через Yandex SpeechKit (потоковый API v3, gRPC).

Держит длинные голосовые (не ограничено 30 секундами). Telegram OggOpus
отправляется как есть — конвертация не нужна. Функция transcribe блокирующая —
вызывать из async-кода через asyncio.to_thread.
"""
import logging

import grpc
from yandex.cloud.ai.stt.v3 import stt_pb2, stt_service_pb2_grpc

from .config import settings

logger = logging.getLogger(__name__)

_HOST = "stt.api.cloud.yandex.net:443"
_CHUNK_BYTES = 16000  # размер аудио-чанка на сообщение


def _requests(audio_path: str):
    options = stt_pb2.StreamingOptions(
        recognition_model=stt_pb2.RecognitionModelOptions(
            audio_format=stt_pb2.AudioFormatOptions(
                container_audio=stt_pb2.ContainerAudio(
                    container_audio_type=stt_pb2.ContainerAudio.OGG_OPUS
                )
            ),
            text_normalization=stt_pb2.TextNormalizationOptions(
                text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
            ),
            language_restriction=stt_pb2.LanguageRestrictionOptions(
                restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                language_code=[settings.yandex_language],
            ),
        )
    )
    yield stt_pb2.StreamingRequest(session_options=options)

    with open(audio_path, "rb") as audio:
        while True:
            data = audio.read(_CHUNK_BYTES)
            if not data:
                break
            yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))


def transcribe(audio_path: str) -> str:
    """Возвращает распознанный текст (русский). Может вернуть пустую строку."""
    if not settings.yandex_api_key:
        raise RuntimeError("YANDEX_API_KEY не задан в .env")

    metadata = [("authorization", f"Api-Key {settings.yandex_api_key}")]
    if settings.yandex_folder_id:
        metadata.append(("x-folder-id", settings.yandex_folder_id))

    channel = grpc.secure_channel(_HOST, grpc.ssl_channel_credentials())
    finals: list[str] = []
    refinements: list[str] = []
    try:
        stub = stt_service_pb2_grpc.RecognizerStub(channel)
        responses = stub.RecognizeStreaming(_requests(audio_path), metadata=metadata)
        for response in responses:
            event = response.WhichOneof("Event")
            if event == "final":
                alts = response.final.alternatives
                if alts:
                    finals.append(alts[0].text)
            elif event == "final_refinement":
                alts = response.final_refinement.normalized_text.alternatives
                if alts:
                    refinements.append(alts[0].text)
    finally:
        channel.close()

    # нормализованный текст (refinement) точнее обычного final
    parts = refinements or finals
    text = " ".join(p.strip() for p in parts if p.strip()).strip()
    logger.info("STT готово (Yandex SpeechKit): %d символов", len(text))
    return text
