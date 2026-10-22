"""
Скрипт проверки конфигурации бота
"""
import os
from dotenv import load_dotenv

def check_config():
    """Проверка настроек бота"""
    print("🔍 Проверка конфигурации бота...\n")

    # Загружаем .env
    load_dotenv()

    # Проверяем токен
    bot_token = os.getenv("BOT_TOKEN")
    if bot_token and bot_token != "your_bot_token_here":
        print("✅ BOT_TOKEN установлен")
    else:
        print("❌ BOT_TOKEN не настроен! Укажите токен в файле .env")
        print("   Получить токен можно у @BotFather в Telegram\n")
        return False

    # Проверяем admin ID
    admin_id = os.getenv("ADMIN_ID")
    if admin_id and admin_id != "your_admin_id_here":
        try:
            int(admin_id)
            print(f"✅ ADMIN_ID установлен: {admin_id}")
        except ValueError:
            print("❌ ADMIN_ID должен быть числом!")
            print("   Узнать свой ID можно у @userinfobot\n")
            return False
    else:
        print("❌ ADMIN_ID не настроен! Укажите ID администратора в файле .env")
        print("   Узнать свой ID можно у @userinfobot\n")
        return False

    # Проверяем путь к базе данных
    db_path = os.getenv("DATABASE_PATH", "data/bot.db")
    db_dir = os.path.dirname(db_path)

    if db_dir and not os.path.exists(db_dir):
        print(f"⚠️ Директория для базы данных не существует: {db_dir}")
        print(f"   Создаем директорию...")
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ Директория создана")
    else:
        print(f"✅ Путь к базе данных: {db_path}")

    print("\n" + "="*50)
    print("✅ Конфигурация проверена успешно!")
    print("="*50)
    print("\n📝 Следующие шаги:")
    print("1. Запустите бота: python bot.py")
    print("2. Откройте бота в Telegram")
    print("3. Отправьте команду /start")
    print("4. Для админ-панели используйте /admin\n")

    return True


if __name__ == "__main__":
    try:
        if check_config():
            print("🚀 Бот готов к запуску!")
        else:
            print("\n⚠️ Исправьте ошибки конфигурации перед запуском бота.")
    except Exception as e:
        print(f"\n❌ Ошибка при проверке конфигурации: {e}")
