"""Клиент блога uRema поверх Supabase (прямой доступ через service_role).

Делает три вещи и кэширует результаты в .bot_cache.json, чтобы не повторять
дорогие операции при каждом посте:
  - находит/создаёт категорию uRema;
  - один раз загружает плейсхолдер в Storage и запоминает его публичный URL;
  - (опц.) резолвит author_id по identifier.

Все функции синхронные (supabase-py sync) — вызывать из async через asyncio.to_thread.
"""
import json
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from supabase import Client, create_client

from .config import settings

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(".bot_cache.json")
_client: Client | None = None
_cache: dict = {}


def _sb() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
    return _client


def _load_cache() -> None:
    global _cache
    if _CACHE_FILE.exists():
        _cache = json.loads(_CACHE_FILE.read_text("utf-8"))


def _save_cache() -> None:
    _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), "utf-8")


def ensure_category_id() -> str:
    if _cache.get("category_id"):
        return _cache["category_id"]

    sb = _sb()
    found = (
        sb.table("categories")
        .select("id")
        .eq("slug", settings.blog_category_slug)
        .limit(1)
        .execute()
    )
    if found.data:
        category_id = found.data[0]["id"]
    else:
        created = (
            sb.table("categories")
            .insert(
                {
                    "name": settings.blog_category_name,
                    "slug": settings.blog_category_slug,
                }
            )
            .execute()
        )
        category_id = created.data[0]["id"]
        logger.info(
            "Создана категория %s (%s)", settings.blog_category_name, category_id
        )

    _cache["category_id"] = category_id
    _save_cache()
    return category_id


def ensure_placeholder_url() -> str:
    if _cache.get("placeholder_url"):
        return _cache["placeholder_url"]

    file_path = Path(settings.placeholder_path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Плейсхолдер не найден: {file_path}. "
            "Положите картинку и/или поправьте PLACEHOLDER_PATH в .env"
        )

    sb = _sb()
    storage_path = settings.placeholder_storage_path
    content_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    try:
        sb.storage.from_(settings.storage_bucket).upload(
            storage_path,
            file_path.read_bytes(),
            {"content-type": content_type, "upsert": "true"},
        )
        logger.info("Плейсхолдер загружен в Storage: %s", storage_path)
    except Exception as error:  # уже существует — не критично
        logger.warning("Загрузка плейсхолдера пропущена: %s", error)

    url = sb.storage.from_(settings.storage_bucket).get_public_url(storage_path)
    _cache["placeholder_url"] = url
    _save_cache()
    return url


def resolve_author_id() -> str | None:
    if not settings.blog_author_identifier:
        return None
    if "author_id" in _cache:
        return _cache["author_id"]

    sb = _sb()
    found = (
        sb.table("users")
        .select("id")
        .eq("identifier", settings.blog_author_identifier)
        .limit(1)
        .execute()
    )
    author_id = found.data[0]["id"] if found.data else None
    if author_id is None:
        logger.warning(
            "Пользователь с identifier=%s не найден, author_id будет пустым",
            settings.blog_author_identifier,
        )
    _cache["author_id"] = author_id
    _save_cache()
    return author_id


def create_draft(content: str) -> dict:
    """Создаёт черновик поста. Возвращает строку blog_posts (с id и title)."""
    now = datetime.now()
    payload = {
        "title": now.strftime(settings.title_date_format),
        "content": content,
        "author": settings.blog_author_name,
        "author_id": resolve_author_id(),
        "image_url": ensure_placeholder_url(),
        "category_id": ensure_category_id(),
        "status": "draft",  # важно: дефолт колонки = 'published', задаём явно
        "slug": now.strftime("%Y-%m-%d-%H%M%S"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = _sb().table("blog_posts").insert(payload).execute()
    post = result.data[0]
    logger.info("Черновик создан: %s (%s)", post["title"], post["id"])
    return post


def edit_link(post_id: str) -> str:
    return f"{settings.site_url.rstrip('/')}/admin/panel/posts/{post_id}"


_load_cache()
