@echo off
echo ========================================
echo   Запуск бота скупки каналов
echo ========================================
echo.

REM Проверка конфигурации
echo Проверка конфигурации...
python check_config.py
echo.

if errorlevel 1 (
    echo.
    echo Ошибка конфигурации! Исправьте настройки в .env
    pause
    exit /b 1
)

echo.
echo Запуск бота...
echo Для остановки нажмите Ctrl+C
echo.
python bot.py

pause