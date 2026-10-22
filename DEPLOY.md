# 🚀 Развертывание бота на сервере

## Варианты развертывания

### 1. Локальный компьютер (Windows/Linux/Mac)
Для тестирования и небольшой нагрузки.

### 2. VPS/VDS сервер
Рекомендуется для продакшена.

### 3. Docker контейнер
Изолированная среда.

---

## 📋 Требования к серверу

### Минимальные требования:
- **CPU:** 1 ядро
- **RAM:** 512 MB
- **Диск:** 1 GB свободного места
- **ОС:** Linux (Ubuntu 20.04+, Debian 10+, CentOS 7+) или Windows Server
- **Python:** 3.8 или выше

### Рекомендуемые требования:
- **CPU:** 2+ ядра
- **RAM:** 1+ GB
- **Диск:** 5+ GB SSD
- **ОС:** Ubuntu 22.04 LTS
- **Python:** 3.10+

---

## 🐧 Развертывание на Ubuntu/Debian

### Шаг 1: Подключение к серверу

```bash
ssh user@your-server-ip
```

### Шаг 2: Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### Шаг 3: Установка Python и pip

```bash
sudo apt install python3 python3-pip python3-venv -y
```

### Шаг 4: Создание директории проекта

```bash
mkdir -p ~/telegram-bot
cd ~/telegram-bot
```

### Шаг 5: Загрузка файлов проекта

**Вариант A: Через Git (если проект в репозитории)**
```bash
git clone https://your-repo-url.git .
```

**Вариант B: Через SCP (с локальной машины)**
```bash
# На локальной машине:
scp -r "c:\Users\SystemX\Desktop\Бот скупка каналов"/* user@your-server-ip:~/telegram-bot/
```

**Вариант C: Через FTP/SFTP**
- Используйте FileZilla или WinSCP
- Загрузите все файлы в `~/telegram-bot/`

### Шаг 6: Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
```

### Шаг 7: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 8: Настройка .env

```bash
nano .env
```

Укажите ваши данные:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_admin_id_here
DATABASE_PATH=data/bot.db
```

Сохраните: `Ctrl + O`, выйдите: `Ctrl + X`

### Шаг 9: Создание директории для базы данных

```bash
mkdir -p data
```

### Шаг 10: Проверка конфигурации

```bash
python3 check_config.py
```

### Шаг 11: Тестовый запуск

```bash
python3 bot.py
```

Если все работает, остановите бота: `Ctrl + C`

---

## 🔄 Автозапуск бота (systemd)

### Создание systemd service

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Вставьте содержимое:
```ini
[Unit]
Description=Telegram Bot for Channel Buying
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/telegram-bot
Environment="PATH=/home/your-username/telegram-bot/venv/bin"
ExecStart=/home/your-username/telegram-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Замените:**
- `your-username` на ваше имя пользователя (узнать: `whoami`)

Сохраните и выйдите.

### Активация сервиса

```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable telegram-bot

# Запустить бота
sudo systemctl start telegram-bot

# Проверить статус
sudo systemctl status telegram-bot
```

### Управление сервисом

```bash
# Остановить бота
sudo systemctl stop telegram-bot

# Перезапустить бота
sudo systemctl restart telegram-bot

# Просмотр логов
sudo journalctl -u telegram-bot -f
```

---

## 🪟 Развертывание на Windows Server

### Шаг 1: Установка Python

1. Скачайте Python с [python.org](https://www.python.org/downloads/)
2. Установите, отметив "Add to PATH"

### Шаг 2: Копирование файлов

Скопируйте папку проекта на сервер

### Шаг 3: Установка зависимостей

```cmd
cd "путь\к\проекту"
pip install -r requirements.txt
```

### Шаг 4: Настройка .env

Откройте `.env` в блокноте и укажите ваши данные

### Шаг 5: Запуск

```cmd
python bot.py
```

### Автозапуск (через Планировщик задач)

1. Откройте "Планировщик задач"
2. Создайте простую задачу
3. Триггер: "При запуске компьютера"
4. Действие: Запустить программу
5. Программа: `python.exe`
6. Аргументы: `bot.py`
7. Рабочая папка: путь к проекту

---

## 🐳 Развертывание через Docker

### Создание Dockerfile

Создайте файл `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

CMD ["python", "bot.py"]
```

### Создание docker-compose.yml

```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    container_name: telegram-bot
    restart: always
    volumes:
      - ./data:/app/data
    env_file:
      - .env
```

### Запуск

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

---

## 🔒 Безопасность

### 1. Настройка файрвола (UFW)

```bash
# Установка
sudo apt install ufw -y

# Разрешить SSH
sudo ufw allow 22/tcp

# Включить файрвол
sudo ufw enable

# Проверить статус
sudo ufw status
```

### 2. Ограничение прав доступа

```bash
# Права на .env (только владелец может читать)
chmod 600 .env

# Права на базу данных
chmod 600 data/bot.db
```

### 3. Регулярные обновления

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Обновление зависимостей Python
pip install --upgrade -r requirements.txt
```

---

## 📊 Мониторинг

### Просмотр логов

```bash
# Логи systemd
sudo journalctl -u telegram-bot -f

# Последние 100 строк
sudo journalctl -u telegram-bot -n 100
```

### Использование ресурсов

```bash
# Загрузка процессора и памяти
top

# Использование диска
df -h

# Использование памяти
free -m
```

### Проверка работоспособности

```bash
# Статус сервиса
sudo systemctl status telegram-bot

# Проверка процесса
ps aux | grep bot.py
```

---

## 💾 Резервное копирование

### Автоматическое резервное копирование базы данных

Создайте скрипт `backup.sh`:

```bash
#!/bin/bash

# Директории
BOT_DIR="/home/your-username/telegram-bot"
BACKUP_DIR="/home/your-username/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Копирование базы данных
cp $BOT_DIR/data/bot.db $BACKUP_DIR/bot_$DATE.db

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "bot_*.db" -mtime +30 -delete

echo "Backup completed: bot_$DATE.db"
```

Сделайте скрипт исполняемым:
```bash
chmod +x backup.sh
```

### Добавление в cron (автоматический запуск каждый день в 3:00)

```bash
crontab -e
```

Добавьте строку:
```
0 3 * * * /home/your-username/telegram-bot/backup.sh
```

---

## 🔄 Обновление бота

### На сервере с Git

```bash
cd ~/telegram-bot
git pull
sudo systemctl restart telegram-bot
```

### Без Git

1. Остановите бота:
```bash
sudo systemctl stop telegram-bot
```

2. Загрузите новые файлы (SCP, FTP)

3. Запустите бота:
```bash
sudo systemctl start telegram-bot
```

---

## ❗ Устранение проблем

### Бот не запускается

**Проверьте логи:**
```bash
sudo journalctl -u telegram-bot -n 50
```

**Проверьте конфигурацию:**
```bash
python3 check_config.py
```

### Ошибка доступа к базе данных

```bash
# Проверьте права
ls -la data/bot.db

# Установите правильные права
chmod 600 data/bot.db
chown your-username:your-username data/bot.db
```

### Бот отстает или медленно работает

**Проверьте ресурсы:**
```bash
top
free -m
df -h
```

**Возможно нужно увеличить RAM или CPU сервера**

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи
2. Проверьте конфигурацию
3. Проверьте ресурсы сервера
4. Обратитесь к разработчику

---

**Успешного развертывания! 🚀**
