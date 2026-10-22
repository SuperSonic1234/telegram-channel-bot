"""
Главный файл бота для скупки каналов
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import Database

# Импортируем обработчики
from handlers import user_handlers, sale_handlers, support_handlers
from admin import admin_handlers, admin_requests, admin_settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота"""
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

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
