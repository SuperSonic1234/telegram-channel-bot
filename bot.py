"""
Главный файл бота для скупки каналов
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from admin import admin_handlers, admin_requests, admin_settings
from config import BOT_TOKEN
from database import Database

# Импортируем обработчики
from handlers import sale_handlers, support_handlers, user_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота"""
    # Инициализация бота
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Инициализация диспетчера
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(user_handlers.router)
    dp.include_router(sale_handlers.router)
    dp.include_router(support_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(admin_requests.router)
    dp.include_router(admin_settings.router)

    # Инициализация базы данных
    db = Database()
    await db.init_db()

    logger.info("Бот запущен!")

    try:
        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
