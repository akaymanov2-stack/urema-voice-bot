"""Точка входа: запуск бота в режиме long polling."""
import asyncio
import logging
import socket

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from .config import settings
from .handlers import router

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def main() -> None:
    setup_logging()

    session = None
    if settings.telegram_force_ipv6:
        session = AiohttpSession()
        session._connector_init["family"] = socket.AF_INET6
        logger.info("Telegram через IPv6 (TELEGRAM_FORCE_IPV6=true)")

    bot = Bot(
        settings.telegram_bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("Бот запущен (long polling). Разрешённые user_id: %s", settings.allowed_ids)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
