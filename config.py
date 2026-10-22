import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env файлу
env_path = Path(__file__).parent / '.env'

# Загрузка переменных окружения
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # ID админа (для управления ботом)
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")

# Курсы и комиссии (обновляются в админке)
DEFAULT_COMMISSION_PERCENT = 30  # Процент прибыли
STARS_TO_GRAM_RATE = 0.01  # Примерный курс
GRAM_TO_RUB_RATE = 100  # Примерный курс
CHANNEL_TRANSFER_HOURS = 24  # Часов на передачу канала