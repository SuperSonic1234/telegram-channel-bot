#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-132.243.194.9}"
SERVER_PORT="${SERVER_PORT:-58595}"
SERVER_USER="${SERVER_USER:-root}"

ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" 'bash -s' <<'SERVER'
set -euo pipefail
cd /root/telegram-channel-bot

git fetch origin main
git reset --hard origin/main

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo "Заполните /root/telegram-channel-bot/.env и повторите запуск." >&2
    exit 1
fi

mkdir -p data
systemctl daemon-reload
systemctl restart telegram-bot
systemctl --no-pager --full status telegram-bot
SERVER
