"""Обработчики процесса продажи канала."""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import Database
from utils.calculator import ChannelPriceCalculator
from utils.keyboards import (
    cancel_sale_kb,
    main_menu_kb,
    payment_method_kb,
)
from utils.validation import parse_finite_number, safe_html

router = Router()
db = Database()
logger = logging.getLogger(__name__)
@router.callback_query(F.data == "main_sell")
async def main_sell_callback(callback: CallbackQuery, state: FSMContext):
    await start_sale(callback.message, state)
    await callback.answer()


class SaleStates(StatesGroup):
    waiting_channel_link = State()
    waiting_total_balance = State()
    waiting_available_balance = State()
    waiting_hold_balance = State()
    waiting_payment_choice = State()
    waiting_payment_details = State()


@router.message(F.text == "💰 Продать канал")
async def start_sale(message: Message, state: FSMContext):
    """Начало процесса продажи канала"""
    await state.clear()

    text = """
💰 <b>Продажа канала</b>

Для расчета стоимости вашего канала нам нужны следующие данные:

1️⃣ Ссылка на канал
2️⃣ Общая сумма баланса
3️⃣ Доступно к выводу
4️⃣ Сумма в холде

Давайте начнем!

🔗 Введите <b>ссылку на ваш канал</b> (например: @channel или t.me/channel):
"""

    await message.answer(text, reply_markup=cancel_sale_kb())
    await state.set_state(SaleStates.waiting_channel_link)


@router.message(SaleStates.waiting_channel_link)
async def process_channel_link(message: Message, state: FSMContext):
    """Обработка ссылки на канал"""
    if not message.text:
        await message.answer("❌ Отправьте ссылку текстом.", reply_markup=cancel_sale_kb())
        return
    channel_link = message.text.strip()

    # Базовая валидация ссылки
    if not (channel_link.startswith('@') or 't.me/' in channel_link or 'telegram.me/' in channel_link):
        await message.answer(
            "❌ Пожалуйста, введите корректную ссылку на канал.\n\n"
            "Формат: @channel или t.me/channel\n\n"
            "Попробуйте еще раз:",
            reply_markup=cancel_sale_kb()
        )
        return

    await state.update_data(channel_link=channel_link)

    text = "✅ Ссылка на канал сохранена!\n\n"
    text += "📊 Теперь введите <b>общую сумму баланса</b> в звездах (Stars):"

    await message.answer(text, reply_markup=cancel_sale_kb())
    await state.set_state(SaleStates.waiting_total_balance)


@router.message(SaleStates.waiting_total_balance)
async def process_total_balance(message: Message, state: FSMContext):
    """Обработка общего баланса"""
    try:
        total_balance = parse_finite_number(message.text)
        if total_balance <= 0:
            raise ValueError

        await state.update_data(total_balance=total_balance)

        text = "✅ Общий баланс сохранен!\n\n"
        text += "📊 Теперь введите сумму <b>доступную к выводу</b> в звездах (Stars):"

        await message.answer(text, reply_markup=cancel_sale_kb())
        await state.set_state(SaleStates.waiting_available_balance)

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число.\n\n"
            "Попробуйте еще раз:",
            reply_markup=cancel_sale_kb()
        )


@router.message(SaleStates.waiting_available_balance)
async def process_available_balance(message: Message, state: FSMContext):
    """Обработка доступного баланса"""
    try:
        available_balance = parse_finite_number(message.text)
        if available_balance < 0:
            raise ValueError

        data = await state.get_data()
        total_balance = data['total_balance']

        if available_balance > total_balance:
            await message.answer(
                "❌ Доступный баланс не может быть больше общего баланса!\n\n"
                "Попробуйте еще раз:",
                reply_markup=cancel_sale_kb()
            )
            return

        await state.update_data(available_balance=available_balance)

        text = "✅ Доступный баланс сохранен!\n\n"
        text += "📊 Теперь введите сумму <b>в холде</b> в звездах (Stars):"

        await message.answer(text, reply_markup=cancel_sale_kb())
        await state.set_state(SaleStates.waiting_hold_balance)

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число.\n\n"
            "Попробуйте еще раз:",
            reply_markup=cancel_sale_kb()
        )


@router.message(SaleStates.waiting_hold_balance)
async def process_hold_balance(message: Message, state: FSMContext):
    """Обработка холд баланса и расчет стоимости"""
    try:
        hold_balance = parse_finite_number(message.text)
        if hold_balance < 0:
            raise ValueError

        data = await state.get_data()
        total_balance = data['total_balance']
        available_balance = data['available_balance']

        minimum_sale_balance = float(await db.get_setting('minimum_sale_balance') or 0)
        if total_balance < minimum_sale_balance:
            await message.answer(
                f"Продажа канала недоступна: минимальный баланс для продажи — "
                f"{minimum_sale_balance:g} Stars.",
                reply_markup=main_menu_kb()
            )
            await state.clear()
            return

        # Проверка: сумма доступного и холда должна соответствовать общему балансу
        if abs((available_balance + hold_balance) - total_balance) > 0.01:
            await message.answer(
                f"❌ Ошибка в данных!\n\n"
                f"Общий баланс: {total_balance}\n"
                f"Доступно + Холд: {available_balance + hold_balance}\n\n"
                f"Суммы не сходятся. Пожалуйста, проверьте данные и начните заново.",
                reply_markup=main_menu_kb()
            )
            await state.clear()
            return

        # Показываем, что идет расчет
        calc_msg = await message.answer("⏳ <b>Идет расчет стоимости канала...</b>\n\n<i>Получаем актуальный курс TON...</i>")

        # Получаем процент прибыли из настроек
        commission_percent = float(await db.get_setting('commission_percent') or 30)

        # Рассчитываем стоимость с актуальными курсами
        calculation = await ChannelPriceCalculator.calculate_channel_price(
            total_balance,  # Используем общий баланс для расчета
            commission_percent
        )

        # Создаем объект цен для совместимости
        prices = {
            'rub': calculation['final_price_rub'],
            'gram': calculation['final_price_gram'],
            'stars': calculation['final_price_stars']
        }

        # Сохраняем заявку в базу
        request_id = await db.create_sale_request(
            message.from_user.id,
            message.from_user.username or "unknown",
            data['channel_link'],
            total_balance,
            available_balance,
            hold_balance,
            prices,
            calculation,
        )

        await state.update_data(
            hold_balance=hold_balance,
            prices=prices,
            profit={
                'rub': round(calculation['rub_after_conversion'] - calculation['final_price_rub'], 2),
                'gram': round(calculation['gram_after_conversion'] - calculation['final_price_gram'], 4),
                'stars': round(calculation['stars_after_fragment'] - calculation['final_price_stars'], 2),
            },
            request_id=request_id
        )

        # Удаляем сообщение о расчете
        await calc_msg.delete()

        # Показываем результат
        result_text = ChannelPriceCalculator.format_price_message(calculation)
        await message.answer(result_text, reply_markup=payment_method_kb())
        await state.set_state(SaleStates.waiting_payment_choice)

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число.\n\n"
            "Попробуйте еще раз:",
            reply_markup=cancel_sale_kb()
        )


@router.callback_query(
    SaleStates.waiting_payment_choice,
    F.data.in_({"payment_rub", "payment_gram", "payment_stars"}),
)
async def process_payment_choice(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка выбора метода оплаты"""
    payment_method = callback.data.split("_")[1]  # rub, gram, stars

    data = await state.get_data()
    request_id = data.get('request_id')
    prices = data.get('prices')
    profit = data.get('profit')
    if not request_id or not prices or not profit:
        await callback.answer("❌ Сессия устарела. Начните заново.", show_alert=True)
        await state.clear()
        return

    request = await db.get_sale_request(request_id)
    if not request or request['user_id'] != callback.from_user.id or request['status'] != 'draft':
        await callback.answer("❌ Эта заявка уже обработана.", show_alert=True)
        await state.clear()
        return

    # Обновляем заявку
    await db.update_sale_request(request_id, payment_method=payment_method)
    if not await db.transition_sale_request(request_id, 'pending', ('draft',)):
        await callback.answer("❌ Эта заявка уже обработана.", show_alert=True)
        await state.clear()
        return

    # Отправляем заявку админу
    admin_text = f"""
🔔 <b>Новая заявка на продажу канала!</b>

👤 Пользователь: @{safe_html(callback.from_user.username or 'unknown')}
🆔 ID: <code>{callback.from_user.id}</code>

📊 <b>Данные канала:</b>
💰 Общий баланс: {data['total_balance']} Stars
✅ Доступно: {data['available_balance']} Stars
🔒 В холде: {data['hold_balance']} Stars

💵 <b>Расчетная стоимость:</b>
🪙 {prices['stars']} Stars
💎 {prices['gram']} GRAM
💵 {prices['rub']} RUB

💰 <b>Чистая прибыль:</b>
⭐ {profit['stars']} Stars
💎 {profit['gram']} GRAM
💵 {profit['rub']} RUB

💳 <b>Желаемый метод оплаты:</b> {payment_method.upper()}

📋 ID заявки: <code>{request_id}</code>
"""

    # Импортируем клавиатуру для админа
    from utils.keyboards import request_action_kb

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=request_action_kb(request_id)
        )
    except Exception:
        logger.exception("Не удалось отправить заявку %s администратору", request_id)

    # Уведомляем пользователя
    user_text = """
✅ <b>Заявка отправлена!</b>

Ваш канал на рассмотрении модератором.
Как только примем решение, вы получите уведомление.

⏳ Ожидайте...
"""

    await callback.message.edit_text(user_text)
    await callback.message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=main_menu_kb()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_sale")
async def cancel_sale(callback: CallbackQuery, state: FSMContext):
    """Отмена продажи канала"""
    data = await state.get_data()
    request_id = data.get('request_id')
    if request_id:
        await db.transition_sale_request(request_id, 'cancelled', ('draft',))
    await state.clear()

    await callback.message.edit_text("❌ Продажа канала отменена.")
    await callback.message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("send_payment_details"))
async def request_payment_details(callback: CallbackQuery, state: FSMContext):
    """Запрос реквизитов для выплаты"""
    # Извлекаем request_id из callback_data если он есть
    request_id = None
    if ":" in callback.data:
        try:
            request_id = int(callback.data.split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer("❌ Некорректная заявка", show_alert=True)
            return

        request = await db.get_sale_request(request_id)
        if (
            not request
            or request['user_id'] != callback.from_user.id
            or request['status'] != 'approved'
        ):
            await callback.answer("❌ Заявка недоступна", show_alert=True)
            return
        # Сохраняем request_id в state
        await state.update_data(request_id=request_id)

    text = """
📝 <b>Отправка реквизитов</b>

Пожалуйста, отправьте ваши реквизиты для получения выплаты:

• Для звезд (Stars) - @username
• Для GRAM - адрес кошелька
• Для рублей (RUB) - номер карты

Введите ваши данные:
"""

    await callback.message.edit_text(text)
    await state.set_state(SaleStates.waiting_payment_details)
    await callback.answer()


@router.message(SaleStates.waiting_payment_details)
async def process_payment_details(message: Message, state: FSMContext, bot: Bot):
    """Обработка реквизитов для выплаты"""
    if not message.text or not message.text.strip():
        await message.answer("❌ Отправьте реквизиты текстом.")
        return
    payment_details = message.text.strip()

    data = await state.get_data()
    request_id = data.get('request_id')

    if not request_id:
        await message.answer(
            "❌ Произошла ошибка. Начните процесс заново.",
            reply_markup=main_menu_kb()
        )
        await state.clear()
        return

    # Получаем данные заявки
    request = await db.get_sale_request(request_id)

    if not request or request['user_id'] != message.from_user.id:
        await message.answer(
            "❌ Произошла ошибка. Заявка не найдена.",
            reply_markup=main_menu_kb()
        )
        await state.clear()
        return

    if request['status'] != 'approved' or not request['payment_method']:
        await message.answer(
            "❌ Эта заявка уже обработана или еще не одобрена.",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    if not await db.transition_sale_request(request_id, 'awaiting_payout', ('approved',)):
        await message.answer("❌ Эта заявка уже обработана.", reply_markup=main_menu_kb())
        await state.clear()
        return
    await db.update_sale_request(request_id, payment_details=payment_details)

    # Создаем запись о выплате
    amount = request['calculated_price_' + request['payment_method']]
    try:
        await db.create_payment(
            request_id,
            message.from_user.id,
            payment_details,
            amount,
            request['payment_method']
        )
    except Exception:
        await db.transition_sale_request(request_id, 'approved', ('awaiting_payout',))
        raise

    # Отправляем админу заявку на выплату
    admin_text = f"""
💳 <b>Заявка на выплату</b>

👤 Пользователь: @{safe_html(message.from_user.username or 'unknown')}
🆔 ID: <code>{message.from_user.id}</code>

💰 Сумма: {request['calculated_price_' + request['payment_method']]} {request['payment_method'].upper()}
💳 Метод: {request['payment_method'].upper()}

📝 <b>Реквизиты:</b>
<code>{safe_html(payment_details)}</code>

📋 ID заявки: <code>{request_id}</code>
"""

    from utils.keyboards import payment_action_kb

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=payment_action_kb(request_id)
        )
    except Exception:
        logger.exception("Не удалось отправить выплату по заявке %s администратору", request_id)

    # Уведомляем пользователя
    user_text = """
✅ <b>Реквизиты отправлены!</b>

Выплата поступит после передачи канала.
Ожидайте подтверждения от модератора.
"""

    await message.answer(user_text, reply_markup=main_menu_kb())
    await state.clear()
