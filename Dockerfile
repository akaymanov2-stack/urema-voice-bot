FROM python:3.11-slim

# libgomp1 нужен ctranslate2 (бэкенд faster-whisper). ffmpeg не нужен — PyAV bundled.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot
COPY assets ./assets

# Кэш моделей HuggingFace — на смонтированный том (см. fly.toml), чтобы
# не скачивать модель при каждом редеплое.
ENV HF_HOME=/data/huggingface

CMD ["python", "-m", "bot.main"]
