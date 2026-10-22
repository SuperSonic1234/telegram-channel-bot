"""
Обработчики для работы с заявками на продажу
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from utils.keyboards import (
    request_action_kb, back_to_admin_kb,
    send_payment_details_kb, reject_reason_kb
)
from config import ADMIN_ID

router = Router()
db = Database()


def is_admin(user_id: int) -> bool:
    """Проверка администратора"""
    return user_id == ADMIN_ID


@router.callback_query(F.data == "admin_requests")
async def show_requests(callback: CallbackQuery):
    """Показать список заявок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    requests = await db.get_pending_requests()

    text = "📋 <b>Заявки на рассмотрении</b>\n\n"

    if not requests:
        text += "Нет ожидающих заявок."
        await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    else:
        text += f"Всего заявок: {len(requests)}\n\n"
        text += "<i>Выберите заявку для работы с ней:</i>"

        # Создаем клавиатуру с кнопками заявок
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = []
        for req in requests[:10]:
            button_text = f"#{req['id']} - @{req['username']} - {req['calculated_price_rub']} RUB"
            keyboard.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_request:{req['id']}"
            )])

        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("view_request:"))
async def view_request_details(callback: CallbackQuery):
    """Показать детали заявки с кнопками действий"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    # Получаем заявку
    request = await db.get_sale_request(request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Формируем детальное описание
    channel_info = f"🔗 <b>Канал:</b> {request['channel_link']}\n" if request.get('channel_link') else ""

    text = f"""
📋 <b>Заявка #{request['id']}</b>

👤 <b>Пользователь:</b> @{request['username']}
🆔 <b>ID:</b> <code>{request['user_id']}</code>
{channel_info}
💰 <b>Баланс канала:</b>
   • Общий баланс: {request['total_balance']} Stars
   • Доступно к выводу: {request['available_balance']} Stars
   • В холде: {request['hold_balance']} Stars

💵 <b>Расчетная стоимость:</b>
   • RUB: {request['calculated_price_rub']}
   • GRAM: {request['calculated_price_gram']}
   • Stars: {request['calculated_price_stars']}

💳 <b>Метод оплаты:</b> {request['payment_method'].upper() if request['payment_method'] else 'не выбрано'}
📅 <b>Создана:</b> {request['created_at']}
"""

    # Показываем с кнопками действий
    await callback.message.edit_text(
        text,
        reply_markup=request_action_kb(request_id)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("approve_request:"))
async def approve_request(callback: CallbackQuery, bot: Bot):
    """Одобрить заявку на продажу"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    # Получаем заявку
    request = await db.get_sale_request(request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Обновляем статус
    await db.update_sale_request(request_id, status='approved')

    # Получаем контакт для передачи канала
    support_contact = await db.get_setting('support_contact') or '@support'

    # Уведомляем пользователя
    user_text = f"""
✅ <b>Ваша заявка одобрена!</b>

Мы готовы купить ваш канал за:
💵 <b>{request['calculated_price_' + request['payment_method']]} {request['payment_method'].upper()}</b>

📋 <b>Следующие шаги:</b>

1️⃣ Передайте права администратора канала на контакт: {support_contact}
⏱ У вас есть 24 часа на передачу канала.

2️⃣ После передачи прав, отправьте реквизиты для получения выплаты, нажав на кнопку ниже.

⚠️ Выплата будет произведена после подтверждения передачи канала.
"""

    try:
        # Отправляем уведомление с request_id в кнопке
        await bot.send_message(
            request['user_id'],
            user_text,
            reply_markup=send_payment_details_kb(request_id)
        )

        # Обновляем сообщение админа
        await callback.message.edit_text(
            f"✅ Заявка #{request_id} одобрена!\n\n"
            f"Пользователь @{request['username']} уведомлен.",
            reply_markup=back_to_admin_kb()
        )

        # Добавляем в историю покупок
        await db.add_purchase(
            request['user_id'],
            request['username'],
            'pending',  # Канал пока не передан
            request['calculated_price_' + request['payment_method']],
            request['payment_method'],
            'approved'
        )

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("reject_request:"))
async def show_reject_reasons(callback: CallbackQuery):
    """Показать причины отказа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    text = """
❌ <b>Отказ в покупке канала</b>

Выберите причину отказа:
"""

    await callback.message.edit_text(text, reply_markup=reject_reason_kb(request_id))
    await callback.answer()


@router.callback_query(F.data.startswith("reject_reason:"))
async def reject_request(callback: CallbackQuery, bot: Bot):
    """Отказать в покупке канала"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    reason_key = parts[1]
    request_id = int(parts[2])

    # Получаем заявку
    request = await db.get_sale_request(request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Обновляем статус
    await db.update_sale_request(request_id, status='rejected')

    # Определяем текст причины
    reasons = {
        'not_transferred': '1. Вы не передали канал в указанные сроки.',
        'wrong_data': '2. Указанные данные не соответствуют действительности.',
        'blocked': '3. Канал заблокирован или имеет ограничения.'
    }

    reason_text = reasons.get(reason_key, 'Не указана')

    # Получаем контакт поддержки
    support_contact = await db.get_setting('support_contact') or '@support'

    # Уведомляем пользователя
    user_text = f"""
❌ <b>В покупке канала отказано</b>

<b>Причина отказа:</b>
{reason_text}

Если вы не согласны с решением, свяжитесь с {support_contact}

📋 Номер заявки: <code>{request_id}</code>
"""

    try:
        await bot.send_message(request['user_id'], user_text)

        # Обновляем сообщение админа
        await callback.message.edit_text(
            f"❌ Заявка #{request_id} отклонена!\n\n"
            f"Причина: {reason_text}\n"
            f"Пользователь @{request['username']} уведомлен.",
            reply_markup=back_to_admin_kb()
        )

        # Добавляем в историю
        await db.add_purchase(
            request['user_id'],
            request['username'],
            'N/A',
            request['calculated_price_' + request['payment_method']],
            request['payment_method'],
            'rejected'
        )

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("payout_done:"))
async def payout_completed(callback: CallbackQuery, bot: Bot):
    """Выплата произведена"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    # Получаем заявку
    request = await db.get_sale_request(request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Обновляем статус
    await db.update_sale_request(request_id, status='completed')

    # Обновляем статистику пользователя
    await db.update_user_stats(
        request['user_id'],
        request['calculated_price_rub']
    )

    # Уведомляем пользователя
    user_text = f"""
✅ <b>Выплата отправлена!</b>

Ваша выплата в размере <b>{request['calculated_price_' + request['payment_method']]} {request['payment_method'].upper()}</b> успешно отправлена.

Спасибо за сотрудничество! 🤝
Ждем вас снова!

💰 Продать еще канал: /start
"""

    try:
        await bot.send_message(request['user_id'], user_text)

        # Обновляем сообщение админа
        await callback.message.edit_text(
            f"✅ Выплата по заявке #{request_id} выполнена!\n\n"
            f"Пользователь @{request['username']} уведомлен.\n"
            f"Сумма: {request['calculated_price_' + request['payment_method']]} {request['payment_method'].upper()}",
            reply_markup=back_to_admin_kb()
        )

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    await callback.answer("✅ Выплата отмечена как выполненная")


@router.callback_query(F.data.startswith("payout_reject:"))
async def payout_rejected(callback: CallbackQuery, bot: Bot):
    """Отказ в выплате"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    # Получаем заявку
    request = await db.get_sale_request(request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Показываем причины отказа
    text = """
❌ <b>Отказ в выплате</b>

Выберите причину отказа:
"""

    await callback.message.edit_text(text, reply_markup=reject_reason_kb(request_id))
    await callback.answer()


@router.callback_query(F.data == "admin_payments")
async def show_payments(callback: CallbackQuery):
    """Показать заявки на выплату"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    # Получаем одобренные заявки с реквизитами
    payments = await db.get_payments_pending()

    text = "💳 <b>Заявки на выплату</b>\n\n"

    if not payments:
        text += "Нет заявок на выплату."
        await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    else:
        text += f"Всего заявок: {len(payments)}\n\n"
        text += "<i>Выберите заявку для работы с ней:</i>"

        # Создаем клавиатуру с кнопками заявок
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = []
        for payment in payments[:10]:
            button_text = f"#{payment['id']} - @{payment['username']} - {payment['amount']} {payment['currency'].upper()}"
            keyboard.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_payment:{payment['request_id']}"
            )])

        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("view_payment:"))
async def view_payment_details(callback: CallbackQuery):
    """Показать детали заявки на выплату"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    # Получаем заявку и платеж
    request = await db.get_sale_request(request_id)
    payment = await db.get_payment_by_request(request_id)

    if not request or not payment:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Формируем детальное описание
    text = f"""
💳 <b>Заявка на выплату #{request['id']}</b>

👤 <b>Пользователь:</b> @{request['username']}
🆔 <b>ID:</b> <code>{request['user_id']}</code>
🔗 <b>Канал:</b> {request['channel_link']}

💰 <b>Сумма выплаты:</b>
{payment['amount']} {payment['currency'].upper()}

📝 <b>Реквизиты:</b>
{payment['payment_details']}

📅 <b>Создана:</b> {request['created_at']}
"""

    # Показываем с кнопками действий
    await callback.message.edit_text(
        text,
        reply_markup=payment_action_kb(request_id)
    )

    await callback.answer()
