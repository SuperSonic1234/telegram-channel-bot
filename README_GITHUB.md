# 🤖 Telegram Channel Bot - Бот для скупки каналов

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.3.0-green.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

Автоматизированный Telegram-бот для покупки каналов с балансом Stars. Включает автоматический расчет цены, работу с курсами валют через API, систему заявок и полную админ-панель.

## ✨ Основные возможности

### 👤 Для пользователей:
- 💰 Продажа Telegram-каналов с балансом Stars
- 🧮 Автоматический расчет стоимости с учетом всех комиссий
- 💳 Выбор способа оплаты: RUB / GRAM / Stars
- 📊 История своих заявок
- 💬 Система поддержки (тикеты с фото/видео)
- 📝 Отслеживание статуса заявок

### 👨‍💼 Для администратора:
- 📊 Полная статистика бота
- 👥 Управление пользователями
- ✅ Одобрение/отклонение заявок
- 💰 Управление выплатами
- 📢 Массовая рассылка
- 💬 Ответы на тикеты поддержки
- 🧮 Калькулятор стоимости
- ⚙️ Настройки бота (процент прибыли, курсы)
- 📜 История всех транзакций

## 🔄 Алгоритм расчета

Бот автоматически рассчитывает итоговую цену по формуле:

```
Баланс Stars (от пользователя)
    ↓ −7%  (Telegram комиссия за вывод)
    ↓ −5%  (Fragment комиссия)
    ↓ ×0.01 (конвертация Stars → GRAM)
    ↓ ×[API] (конвертация GRAM → RUB, курс от CoinGecko)
    ↓ −30% (ваша прибыль, настраивается)
= Итоговая цена для клиента
```

### Пример:
```
10,000 Stars
→ 9,300 (−7% Telegram)
→ 8,835 (−5% Fragment)
→ 88.35 GRAM (×0.01)
→ 25,223.93 RUB (×285.50 от API)
→ 17,656.75 RUB (−30% прибыль)
```

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/SuperSonic1234/telegram-channel-bot.git
cd telegram-channel-bot
```

### 2. Установка зависимостей

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Настройка

Создайте файл `.env`:

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_ID=your_telegram_id
DATABASE_PATH=data/bot.db
```

### 4. Запуск

```bash
python bot.py
```

## 📦 Технологии

- **Python 3.8+**
- **aiogram 3.3.0** - современная асинхронная библиотека для Telegram Bot API
- **aiosqlite** - асинхронная работа с SQLite
- **aiohttp** - HTTP-клиент для API запросов
- **CoinGecko API** - получение актуальных курсов криптовалют

## 📁 Структура проекта

```
telegram-channel-bot/
├── bot.py                    # Главный файл запуска
├── config.py                 # Конфигурация
├── database.py               # Работа с БД
├── requirements.txt          # Зависимости
├── .env                      # Конфигурация (создать вручную)
├── handlers/
│   ├── start_handlers.py     # Команды /start, /help
│   ├── sale_handlers.py      # Продажа каналов
│   └── support_handlers.py   # Система поддержки
├── admin/
│   ├── admin_handlers.py     # Админ-панель
│   └── request_handlers.py   # Обработка заявок
└── utils/
    ├── keyboards.py          # Клавиатуры
    ├── calculator.py         # Расчет цены
    └── rates.py              # API курсов валют
```

## 🐳 Деплой на сервер

### Вариант 1: Через systemd (рекомендуется)

```bash
# 1. Клонируйте репозиторий
cd /root
git clone https://github.com/SuperSonic1234/telegram-channel-bot.git
cd telegram-channel-bot

# 2. Установите зависимости
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Создайте .env
nano .env

# 4. Создайте systemd сервис
sudo nano /etc/systemd/system/telegram-bot.service
```

Содержимое `telegram-bot.service`:

```ini
[Unit]
Description=Telegram Channel Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-channel-bot
Environment="PATH=/root/telegram-channel-bot/.venv/bin"
ExecStart=/root/telegram-channel-bot/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 5. Запустите сервис
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# 6. Проверьте статус
sudo systemctl status telegram-bot
```

### Управление сервисом

```bash
# Статус
sudo systemctl status telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Остановка
sudo systemctl stop telegram-bot

# Логи
sudo journalctl -u telegram-bot -f
```

## 📊 API для курсов

Бот использует **CoinGecko API** для получения актуального курса TON/RUB.

- **Бесплатно**: Не требует регистрации
- **Лимиты**: 10-30 запросов/мин
- **Резервный курс**: 100 RUB/TON (если API недоступен)

Подробнее в файле `RATES_API.md`

## 🔧 Настройка

После первого запуска доступны настройки через админ-панель:

- `commission_percent` - процент прибыли (по умолчанию 30%)
- `stars_withdrawal_commission` - комиссия Telegram (7%)
- `fragment_commission` - комиссия Fragment (5%)
- `stars_to_gram_rate` - курс Stars → GRAM (0.01)

## 📝 Документация

- `README.md` - Основная документация
- `QUICKSTART.md` - Быстрый старт за 3 минуты
- `START_BOT.md` - Подробная инструкция
- `RATES_API.md` - Работа с API курсов
- `DEPLOYMENT_SUMMARY.md` - Итоги деплоя

## 🤝 Поддержка

Если возникли проблемы:

1. Проверьте логи: `journalctl -u telegram-bot -n 50`
2. Убедитесь что `.env` файл правильно заполнен
3. Проверьте версию Python: `python3 --version` (нужен 3.8+)
4. Проверьте что порт не занят другим процессом

## 📜 Лицензия

MIT License - свободное использование

## 👨‍💻 Автор

Создано с помощью Claude Code - 2026

---

⭐ Если проект полезен - поставьте звезду на GitHub!
