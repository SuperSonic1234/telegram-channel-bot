# 📚 Документация проекта

## 🚀 Быстрый старт

### Для новичков:
1. **[QUICKSTART.md](QUICKSTART.md)** - запуск бота за 3 минуты
2. **[START_BOT.md](START_BOT.md)** - подробная инструкция по запуску и решению проблем

### Для продвинутых:
1. **[README.md](README.md)** - полная документация проекта
2. **[CHANGELOG.md](CHANGELOG.md)** - история изменений

---

## 📖 Основная документация

| Файл | Описание |
|------|----------|
| **[README.md](README.md)** | Полная документация: установка, настройка, использование |
| **[QUICKSTART.md](QUICKSTART.md)** | Быстрый старт - минимум текста, максимум действий |
| **[START_BOT.md](START_BOT.md)** | Инструкция по запуску и устранению проблем |
| **[FEATURES.md](FEATURES.md)** | Полный список функций и возможностей бота |
| **[RATES_API.md](RATES_API.md)** | Подробно про автоматические курсы и CoinGecko API |
| **[CHANGELOG.md](CHANGELOG.md)** | История всех изменений проекта |

---

## 🎯 По задачам

### Я хочу запустить бота
→ **[QUICKSTART.md](QUICKSTART.md)** или **[START_BOT.md](START_BOT.md)**

### Бот не запускается
→ **[START_BOT.md](START_BOT.md)** раздел "Проблемы при запуске"

### Хочу узнать все возможности
→ **[FEATURES.md](FEATURES.md)**

### Как работает расчет стоимости?
→ **[RATES_API.md](RATES_API.md)** или **[README.md](README.md)** раздел "Алгоритм расчета"

### Откуда берутся курсы валют?
→ **[RATES_API.md](RATES_API.md)**

### Что нового в последней версии?
→ **[CHANGELOG.md](CHANGELOG.md)**

---

## 🔧 Техническая документация

### Структура кода:

```
Бот скупка каналов/
├── bot.py                      # Точка входа
├── config.py                   # Конфигурация
├── database.py                 # База данных
├── handlers/                   # Обработчики пользователей
│   ├── user_handlers.py       
│   ├── sale_handlers.py       
│   └── support_handlers.py    
├── admin/                      # Админ-панель
│   ├── admin_handlers.py      
│   ├── admin_requests.py      
│   └── admin_settings.py      
└── utils/                      # Утилиты
    ├── calculator.py          # Расчет с актуальными курсами
    ├── rates.py               # CoinGecko API интеграция
    └── keyboards.py           
```

### Ключевые модули:

**utils/rates.py**
- Получение курса TON/RUB через CoinGecko API
- Класс `RatesService` с методами `get_ton_to_rub_rate()`, `get_ton_to_usd_rate()`
- Функция `get_actual_rates()` для получения всех курсов
- Подробнее: [RATES_API.md](RATES_API.md)

**utils/calculator.py**
- 5-шаговый алгоритм расчета стоимости
- Учет комиссий Telegram (7%) и Fragment (5%)
- Автоматическое получение курсов
- Методы:
  - `calculate_channel_price()` - основной расчет
  - `calculate_net_amount()` - для калькулятора админа
  - `format_price_message()` - форматирование для пользователя

**database.py**
- Асинхронная работа с SQLite через aiosqlite
- Таблицы: users, sale_requests, purchase_history, support_tickets, bot_settings
- Все методы async

---

## 📊 Алгоритм расчета (кратко)

```
10,000 Stars
    ↓ −7% Telegram
9,300 Stars
    ↓ −5% Fragment
8,835 Stars
    ↓ ×0.01 (Stars→GRAM)
88.35 GRAM
    ↓ ×285.50 RUB/TON (API)
25,223.93 RUB
    ↓ −30% прибыль
17,656.75 RUB
```

Подробнее: [RATES_API.md](RATES_API.md#расчет-стоимости-канала)

---

## 🌐 API интеграции

### CoinGecko API
- **Endpoint:** `https://api.coingecko.com/api/v3/simple/price`
- **Параметры:** `ids=the-open-network&vs_currencies=rub`
- **Без регистрации:** ✅ Бесплатно
- **Лимит:** ~10-50 запросов/минуту
- **Fallback:** 100 RUB/TON при недоступности

Документация: [RATES_API.md](RATES_API.md#coingecko-api)

---

## 🔐 Безопасность

### Не публикуйте:
- `.env` файл
- Токен бота (`BOT_TOKEN`)
- ID администратора (`ADMIN_ID`)
- База данных `data/bot.db`

### Регулярно делайте:
- Бэкапы базы данных
- Проверку логов на ошибки
- Обновление зависимостей

---

## 📝 Зависимости

```
aiogram==3.3.0          # Telegram Bot API
aiosqlite==0.19.0       # Async SQLite
python-dotenv==1.0.0    # Environment variables
aiohttp==3.9.1          # HTTP requests (CoinGecko API)
requests==2.31.0        # HTTP requests (backup)
```

---

## 🆕 Последнее обновление

**Версия:** 1.1.0  
**Дата:** 2026-10-22

### Главные изменения:
✅ Автоматические курсы через CoinGecko API  
✅ Учет комиссии Fragment (5%)  
✅ 5-шаговый алгоритм расчета  
✅ Детальный breakdown расчета  

Полный список: [CHANGELOG.md](CHANGELOG.md)

---

## 💬 Поддержка

### Частые вопросы:

**Q: Бот не запускается, ошибка Conflict**  
A: Остановите все процессы: `taskkill /F /IM python.exe`, затем запустите снова

**Q: Где взять BOT_TOKEN?**  
A: У @BotFather в Telegram командой `/newbot`

**Q: Где взять ADMIN_ID?**  
A: У @userinfobot в Telegram

**Q: Курс не обновляется**  
A: Проверьте интернет. Бот использует резервное значение при недоступности API

**Q: Можно ли изменить процент прибыли?**  
A: Да, в админ-панели → Настройки

**Q: База данных повреждена**  
A: Удалите `data/bot.db` и перезапустите бота

---

## ✅ Чек-лист перед запуском

- [ ] Python 3.8+ установлен
- [ ] Зависимости установлены: `pip install -r requirements.txt`
- [ ] Файл `.env` создан и заполнен
- [ ] `BOT_TOKEN` получен от @BotFather
- [ ] `ADMIN_ID` получен от @userinfobot
- [ ] Никаких других процессов бота не запущено
- [ ] Порт не занят другим приложением
- [ ] Есть интернет-соединение

---

## 🎓 Дополнительные материалы

- [Официальная документация aiogram](https://docs.aiogram.dev/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [CoinGecko API Docs](https://www.coingecko.com/en/api/documentation)
- [Python async/await](https://docs.python.org/3/library/asyncio.html)

---

**Все готово к работе! Выберите нужный раздел документации выше.**
