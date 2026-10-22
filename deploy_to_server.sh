#!/bin/bash

# ===========================================
# АВТОМАТИЧЕСКИЙ ДЕПЛОЙ БОТА НА СЕРВЕР
# ===========================================

echo "=== 🚀 ДЕПЛОЙ TELEGRAM БОТА ==="
echo ""
echo "📦 Репозиторий: https://github.com/SuperSonic1234/telegram-channel-bot"
echo "🖥️  Сервер: 132.243.194.9:58595"
echo ""

# Подключаемся к серверу и выполняем команды
ssh -p 58595 root@132.243.194.9 << 'SERVEREOF'

echo "=== ✅ Подключение к серверу ==="
uname -a
python3 --version
echo ""

echo "=== Шаг 1/5: Клонирование репозитория ==="
cd /root
if [ -d "telegram-channel-bot" ]; then
  echo "⚠️  Папка существует, удаляем..."
  rm -rf telegram-channel-bot
fi

git clone https://github.com/SuperSonic1234/telegram-channel-bot.git
cd telegram-channel-bot
echo "✅ Репозиторий склонирован"
echo ""

echo "=== Шаг 2/5: Установка зависимостей ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Зависимости установлены"
echo ""

echo "=== Шаг 3/5: Создание .env файла ==="
cat > .env << 'ENVEOF'
BOT_TOKEN=8946911601:AAGBisB9ZAhsY7sYe-ZSc8P8_PEKHN6VOMI
ADMIN_ID=970377911
DATABASE_PATH=data/bot.db
ENVEOF
chmod 600 .env
mkdir -p data
echo "✅ .env создан, папка data готова"
echo ""

echo "=== Шаг 4/5: Настройка systemd ==="
cat > /etc/systemd/system/telegram-bot.service << 'SERVICEEOF'
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
SERVICEEOF

systemctl daemon-reload
systemctl enable telegram-bot
echo "✅ systemd сервис настроен"
echo ""

echo "=== Шаг 5/5: Запуск бота ==="
systemctl start telegram-bot
sleep 3
systemctl status telegram-bot --no-pager
echo ""
echo "=== ✅✅✅ БОТ ЗАПУЩЕН! ✅✅✅ ==="
echo ""
echo "📊 Команды для управления:"
echo "  sudo systemctl status telegram-bot    # Статус"
echo "  sudo systemctl restart telegram-bot   # Перезапуск"
echo "  sudo journalctl -u telegram-bot -f    # Логи"

SERVEREOF

echo ""
echo "🎉 ДЕПЛОЙ ЗАВЕРШЕН!"
