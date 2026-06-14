"""Одноразовый помощник для настройки .env.

Запуск из корня проекта:  python -m tools.setup

Делает два дела:
  1) Печатает список пользователей блога — выберите identifier автора
     для BLOG_AUTHOR_IDENTIFIER.
  2) Запускает polling и печатает Telegram-идентификаторы:
       - напишите боту в личку  -> получите свой user_id (для ALLOWED_USER_IDS);
       - опубликуйте любое сообщение в канале (бот должен быть админом)
         -> получите числовой chat.id канала (для CHANNEL_ID, вида -100...).
Выход — Ctrl+C.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from supabase import create_client

from bot.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def list_users() -> None:
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    res = (
        sb.table("users")
        .select("id, identifier, username, display_name, role")
        .execute()
    )
    print("\n=== Пользователи блога ===")
    for u in res.data:
        print(
            f"  identifier={u['identifier']!r}  username={u.get('username')!r}  "
            f"display_name={u.get('display_name')!r}  role={u['role']}"
        )
    print("→ Возьмите identifier нужного автора в BLOG_AUTHOR_IDENTIFIER\n")


async def main() -> None:
    list_users()

    bot = Bot(settings.telegram_bot_token)
    dp = Dispatcher()

    @dp.message()
    async def on_message(message: Message) -> None:
        user = message.from_user
        user_id = user.id if user else None
        print(
            f"[{message.chat.type.upper()}] chat.id = {message.chat.id}"
            f"  title={message.chat.title!r}"
            f"  from user_id = {user_id} (@{user.username if user else None})"
        )
        if message.chat.type == "private":
            await message.answer(f"Ваш user_id: {user_id}")

    @dp.channel_post()
    async def on_channel(message: Message) -> None:
        print(f"[CHANNEL] chat.id = {message.chat.id}  title={message.chat.title!r}")

    print(
        "Polling запущен. Напишите боту в личку и опубликуйте сообщение в канале.\n"
        "Скопируйте напечатанные id в .env. Выход — Ctrl+C.\n"
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
