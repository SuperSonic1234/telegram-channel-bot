# 🚀 Запуск бота

## ⚠️ Важно перед запуском

### Проверьте, что бот не запущен дважды

Если видите ошибку:
```
TelegramConflictError: Conflict: terminated by other getUpdates request
```

Это означает, что бот уже запущен в другом процессе.

### Остановите все процессы бота:

**Windows:**
```cmd
taskkill /F /IM python.exe
```

**Linux/Mac:**
```bash
pkill -f bot.py
```

---

## 🟢 Запуск бота

### 1. Откройте терминал в папке проекта

```bash
cd "c:\Users\SystemX\Desktop\Бот скупка каналов"
```

### 2. Убедитесь что зависимости установлены

```bash
pip install -r requirements.txt
```

### 3. Проверьте файл .env

Откройте `.env` и убедитесь что заполнены:
- `BOT_TOKEN` - токен от @BotFather
- `ADMIN_ID` - ваш Telegram ID

### 4. Запустите бота

```bash
python bot.py
```

### ✅ Успешный запуск

Вы должны увидеть:
```
2026-10-22 XX:XX:XX - __main__ - INFO - Бот запущен!
2026-10-22 XX:XX:XX - aiogram.dispatcher - INFO - Start polling
2026-10-22 XX:XX:XX - aiogram.dispatcher - INFO - Run polling for bot @YourBot id=...
```

---

## 🛑 Остановка бота

Нажмите `Ctrl+C` в терминале где запущен бот.

---

## 🐛 Проблемы при запуске

### 1. ModuleNotFoundError

```
ModuleNotFoundError: No module named 'aiogram'
```

**Решение:**
```bash
pip install -r requirements.txt
```

### 2. Неверный токен

```
TelegramUnauthorizedError: 401: Unauthorized
```

**Решение:**
- Проверьте токен в `.env`
- Получите новый токен у @BotFather

### 3. Конфликт процессов

```
TelegramConflictError: Conflict: terminated by other getUpdates
```

**Решение:**
```bash
# Остановите все Python процессы
taskkill /F /IM python.exe

# Запустите снова
python bot.py
```

### 4. База данных заблокирована

```
sqlite3.OperationalError: database is locked
```

**Решение:**
```bash
# Удалите файл базы (данные будут потеряны!)
del data\bot.db

# Запустите бота - база создастся заново
python bot.py
```

### 5. Нет доступа к API

```
WARNING - Failed to fetch TON rate, using default
```

**Это не ошибка!** Бот продолжит работу с резервным курсом 100 RUB/TON.

Проверьте интернет-соединение. Когда CoinGecko API станет доступен, курс обновится автоматически.

---

## 📊 Проверка работы

### Для пользователя:
1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Должно прийти приветственное сообщение

### Для администратора:
1. Отправьте `/admin`
2. Должна открыться админ-панель
3. Если нет - проверьте `ADMIN_ID` в `.env`

---

## 💡 Рекомендации

### Запуск в фоне (Linux/Mac):

```bash
nohup python bot.py > bot.log 2>&1 &
```

### Автозапуск при старте системы:

**Windows (Task Scheduler):**
1. Откройте Task Scheduler
2. Create Basic Task
3. Trigger: At system startup
4. Action: Start a program
5. Program: `python.exe`
6. Arguments: `c:\Users\SystemX\Desktop\Бот скупка каналов\bot.py`

**Linux (systemd):**
Создайте `/etc/systemd/system/telegram-bot.service`:
```ini
[Unit]
Description=Telegram Channel Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

---

## 📝 Логи

Все логи выводятся в консоль. Для сохранения в файл:

```bash
python bot.py > bot.log 2>&1
```

Или в реальном времени с выводом:

```bash
python bot.py 2>&1 | tee bot.log
```

---

✅ **Готово! Бот должен работать.**

Вопросы? См. [README.md](README.md) или [QUICKSTART.md](QUICKSTART.md)
