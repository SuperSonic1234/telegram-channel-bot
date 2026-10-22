@echo off
chcp 65001 >nul
set PYTHONUTF8=1
echo ========================================
echo   Запуск бота скупки каналов
echo ========================================
echo.

REM Проверка конфигурации
echo Проверка конфигурации...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

%PYTHON% check_config.py
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
%PYTHON% bot.py

pause
