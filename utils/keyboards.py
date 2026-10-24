"""
Модуль с клавиатурами для бота
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


# === Главное меню ===
def main_menu_kb(is_admin=False):
    keyboard_layout = [
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💬 Поддержка")],
        [KeyboardButton(text="💰 Продать канал")]
    ]

    if is_admin:
        keyboard_layout.append([KeyboardButton(text="🛠 Панель администратора")])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True
    )
    return keyboard


# === Клавиатуры для продажи канала ===
def payment_method_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Рубли (RUB)", callback_data="payment_rub")],
        [InlineKeyboardButton(text="💎 GRAM", callback_data="payment_gram")],
        [InlineKeyboardButton(text="🪙 Stars", callback_data="payment_stars")],
        [InlineKeyboardButton(text="❌ Отменить продажу", callback_data="cancel_sale")]
    ])
    return keyboard


def cancel_sale_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_sale")]
    ])
    return keyboard


def send_payment_details_kb(request_id: int | None = None):
    callback_data = f"send_payment_details:{request_id}" if request_id else "send_payment_details"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Отправить реквизиты", callback_data=callback_data)]
    ])
    return keyboard


# === Клавиатуры для поддержки ===
def support_menu_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать", callback_data="support_write")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard


def back_to_main_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard


# === Админ панель ===
def admin_panel_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📋 Заявки", callback_data="admin_requests")],
        [InlineKeyboardButton(text="💳 Выплаты", callback_data="admin_payments")],
        [InlineKeyboardButton(text="🗂 Архив заявок", callback_data="admin_archive")],
        [InlineKeyboardButton(text="💬 Обращения", callback_data="admin_support")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📜 История скупки", callback_data="admin_history")],
        [InlineKeyboardButton(text="🧮 Калькулятор", callback_data="admin_calculator")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")]
    ])
    return keyboard


def admin_history_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купленные каналы", callback_data="admin_bought")],
        [InlineKeyboardButton(text="❌ Отказанные", callback_data="admin_rejected")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    return keyboard


def admin_settings_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Приветственное сообщение", callback_data="settings_welcome")],
        [InlineKeyboardButton(text="💰 Процент комиссии", callback_data="settings_commission")],
        [InlineKeyboardButton(text="📊 Минимальный баланс продажи", callback_data="settings_minimum_sale_balance")],
        [InlineKeyboardButton(text="📞 Контакт поддержки", callback_data="settings_support_contact")],
        [InlineKeyboardButton(text="💱 Курсы Stars / GRAM / RUB", callback_data="settings_rates")],
        [InlineKeyboardButton(text="💸 Комиссия вывода с канала", callback_data="settings_withdrawal_fee")],
        [InlineKeyboardButton(text="💎 Комиссия Fragment", callback_data="settings_fragment_fee")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    return keyboard


def rates_settings_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💱 Курс за 1 GRAM", callback_data="settings_gram_rate")],
        [InlineKeyboardButton(text="⭐ Курс за 1 Star", callback_data="settings_stars_rate")],
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="admin_settings")]
    ])
    return keyboard


def request_action_kb(request_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить", callback_data=f"approve_request:{request_id}")],
        [InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_request:{request_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_requests")]
    ])
    return keyboard


def request_archive_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в архив", callback_data="admin_archive")],
        [InlineKeyboardButton(text="◀️ В админку", callback_data="admin_panel")],
    ])


def payment_action_kb(request_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выплатить", callback_data=f"payout_done:{request_id}")],
        [InlineKeyboardButton(text="❌ Отказать", callback_data=f"payout_reject:{request_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_requests")]
    ])
    return keyboard


def reject_reason_kb(request_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Не передан канал", callback_data=f"reject_reason:not_transferred:{request_id}")],
        [InlineKeyboardButton(text="Данные не соответствуют", callback_data=f"reject_reason:wrong_data:{request_id}")],
        [InlineKeyboardButton(text="Блок/запрет", callback_data=f"reject_reason:blocked:{request_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_requests")]
    ])
    return keyboard


def payout_reject_reason_kb(request_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Некорректные реквизиты",
            callback_data=f"payout_reject_reason:wrong_details:{request_id}",
        )],
        [InlineKeyboardButton(
            text="Канал не передан",
            callback_data=f"payout_reject_reason:not_transferred:{request_id}",
        )],
        [InlineKeyboardButton(
            text="Нарушение условий сделки",
            callback_data=f"payout_reject_reason:terms_violation:{request_id}",
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_payments")],
    ])


def ticket_action_kb(ticket_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"ticket_reply:{ticket_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_support")]
    ])
    return keyboard


def back_to_admin_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")]
    ])
    return keyboard


def confirm_broadcast_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_panel")]
    ])
    return keyboard
