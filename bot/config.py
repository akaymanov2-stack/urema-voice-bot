"""Конфигурация бота. Все секреты читаются из .env, в коде их нет."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Telegram ---
    telegram_bot_token: str
    allowed_user_ids: str  # список user_id через запятую, например "12345,67890"
    channel_id: str  # @username канала или числовой id вида -100...

    # --- Supabase (прямой доступ к БД блога) ---
    supabase_url: str
    supabase_service_role_key: str

    # --- Блог uRema ---
    site_url: str = "https://i-home-indol.vercel.app"
    blog_author_name: str = "uRema"
    blog_author_identifier: str = ""  # опционально: identifier пользователя для author_id
    blog_category_name: str = "uRema"
    blog_category_slug: str = "urema"
    storage_bucket: str = "blog-images"
    placeholder_path: str = "assets/placeholder.png"  # локальный файл-заглушка
    placeholder_storage_path: str = "images/urema-placeholder.png"  # путь в Storage
    title_date_format: str = "%d.%m.%Y"

    # --- STT (faster-whisper) ---
    whisper_model: str = "medium"  # small / medium / large-v3
    whisper_device: str = "cpu"  # cpu / cuda
    whisper_compute_type: str = "int8"  # int8 (cpu) / float16 (gpu)
    whisper_language: str = "ru"

    # --- Сообщения ---
    channel_message: str = "Текст размещён"

    @property
    def allowed_ids(self) -> set[int]:
        return {
            int(x)
            for x in self.allowed_user_ids.replace(" ", "").split(",")
            if x
        }


settings = Settings()
