#!/usr/bin/env bash
set -euo pipefail

cd /root
if [ ! -d telegram-channel-bot/.git ]; then
    git clone https://github.com/SuperSonic1234/telegram-channel-bot.git
fi

cd telegram-channel-bot
git fetch origin main
git reset --hard origin/main

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo "Заполните .env перед запуском бота." >&2
    exit 1
fi

mkdir -p data
systemctl daemon-reload
systemctl enable telegram-bot
systemctl restart telegram-bot
systemctl --no-pager --full status telegram-bot
