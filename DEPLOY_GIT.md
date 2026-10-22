# 🚀 Деплой бота на сервер через Git

## 📋 Подготовка (выполнено)

✅ Git репозиторий инициализирован  
✅ Файлы добавлены и закоммичены  
✅ .gitignore настроен (исключает .env, БД, логи)  
✅ .env.example создан как шаблон  

---

## 🔗 Шаг 1: Подключение удаленного репозитория

### Вариант A: GitHub

1. Создайте репозиторий на https://github.com/new
2. Подключите:
```bash
git remote add origin https://github.com/username/telegram-channel-bot.git
git branch -M main
git push -u origin main
```

### Вариант B: GitLab

```bash
git remote add origin https://gitlab.com/username/telegram-channel-bot.git
git branch -M main
git push -u origin main
```

---

## 🖥️ Шаг 2: Подготовка сервера

```bash
ssh user@your-server.com

# Установка зависимостей
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

---

## 📥 Шаг 3: Клонирование на сервер

```bash
cd ~
git clone https://github.com/username/telegram-channel-bot.git
cd telegram-channel-bot
```

---

## ⚙️ Шаг 4: Настройка

```bash
# Виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Конфигурация
cp .env.example .env
nano .env  # заполните BOT_TOKEN и ADMIN_ID

# Создайте папку для БД
mkdir -p data
```

---

## 🚀 Шаг 5: Автозапуск (systemd)

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Содержимое:
```ini
[Unit]
Description=Telegram Channel Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/telegram-channel-bot
Environment="PATH=/home/your-username/telegram-channel-bot/.venv/bin"
ExecStart=/home/your-username/telegram-channel-bot/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

---

## 🔄 Обновление бота

```bash
cd ~/telegram-channel-bot
sudo systemctl stop telegram-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start telegram-bot
```

---

## 📊 Управление

```bash
# Статус
sudo systemctl status telegram-bot

# Логи
sudo journalctl -u telegram-bot -f

# Перезапуск
sudo systemctl restart telegram-bot
```

---

✅ Готово! Бот работает на сервере с автозапуском.
