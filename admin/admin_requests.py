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

        for req in requests[:10]:
            text += f"📋 Заявка #{req['id']}\n"
            text += f"👤 @{req['username']} (ID: <code>{req['user_id']}</code>)\n"
            text += f"💰 Баланс: {req['total_balance']} Stars\n"
            text += f"💵 Цена: {req['calculated_price_rub']} RUB\n"
            text += f"💳 Оплата: {req['payment_method'] or 'не выбрано'}\n"
            text += f"📅 {req['created_at']}\n"
            text += "─" * 30 + "\n\n"

        if len(requests) > 10:
            text += f"\n... и еще {len(requests) - 10} заявок"

        text += "\n<i>Для работы с заявкой используйте кнопки под сообщением с деталями заявки</i>"

        await callback.message.edit_text(text, reply_markup=back_to_admin_kb())

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
        # Сохраняем request_id в состоянии для дальнейшей работы
        # (это делается через callback_data или через хранение в базе)
        await bot.send_message(
            request['user_id'],
            user_text,
            reply_markup=send_payment_details_kb()
        )

        # Обновляем сообщение админа
        await callback.message.edit_text(
            f"✅ Заявка #{request_id} одобрена!\n\n"
            f"Пользователь @{request['username']} уведомлен."
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
            f"Пользователь @{request['username']} уведомлен."
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
            f"Сумма: {request['calculated_price_' + request['payment_method']]} {request['payment_method'].upper()}"
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
