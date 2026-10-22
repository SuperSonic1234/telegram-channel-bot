#!/bin/bash
# ===========================================
# СКОПИРУЙТЕ ВСЁ И ВСТАВЬТЕ НА СЕРВЕРЕ
# ===========================================

echo "=== 🚀 АВТОМАТИЧЕСКИЙ ДЕПЛОЙ БОТА ==="
echo ""

# Шаг 1: Клонирование
echo "📥 Шаг 1/5: Клонирование репозитория..."
cd /root
rm -rf telegram-channel-bot 2>/dev/null
git clone https://github.com/SuperSonic1234/telegram-channel-bot.git
cd telegram-channel-bot
echo "✅ Репозиторий склонирован"
echo ""

# Шаг 2: Установка зависимостей
echo "📦 Шаг 2/5: Установка зависимостей..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Зависимости установлены"
echo ""

# Шаг 3: Конфигурация
echo "⚙️  Шаг 3/5: Создание конфигурации..."
cat > .env << 'ENVEOF'
BOT_TOKEN=8946911601:AAGBisB9ZAhsY7sYe-ZSc8P8_PEKHN6VOMI
ADMIN_ID=970377911
DATABASE_PATH=data/bot.db
ENVEOF
chmod 600 .env
mkdir -p data
echo "✅ Конфигурация создана"
echo ""

# Шаг 4: Systemd сервис
echo "🔧 Шаг 4/5: Настройка автозапуска..."
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
echo "✅ Автозапуск настроен"
echo ""

# Шаг 5: Запуск
echo "🚀 Шаг 5/5: Запуск бота..."
systemctl start telegram-bot
sleep 3
echo ""
systemctl status telegram-bot --no-pager
echo ""
echo "=== ✅ ДЕПЛОЙ ЗАВЕРШЕН! ==="
echo ""
echo "📊 Полезные команды:"
echo "  systemctl status telegram-bot      # Статус"
echo "  systemctl restart telegram-bot     # Перезапуск"
echo "  journalctl -u telegram-bot -f      # Логи"
echo ""
