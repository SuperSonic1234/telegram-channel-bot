"""
Обработчики для процесса продажи канала
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from utils.keyboards import (
    main_menu_kb, payment_method_kb, cancel_sale_kb,
    send_payment_details_kb
)
from utils.calculator import ChannelPriceCalculator
from config import ADMIN_ID

router = Router()
db = Database()


class SaleStates(StatesGroup):
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

1️⃣ Общая сумма баланса
2️⃣ Доступно к выводу
3️⃣ Сумма в холде

Давайте начнем!

📊 Введите <b>общую сумму баланса</b> в звездах (Stars):
"""

    await message.answer(text, reply_markup=cancel_sale_kb())
    await state.set_state(SaleStates.waiting_total_balance)


@router.message(SaleStates.waiting_total_balance)
async def process_total_balance(message: Message, state: FSMContext):
    """Обработка общего баланса"""
    try:
        total_balance = float(message.text.replace(',', '.'))
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
        available_balance = float(message.text.replace(',', '.'))
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
async def process_hold_balance(message: Message, state: FSMContext, bot: Bot):
    """Обработка холд баланса и расчет стоимости"""
    try:
        hold_balance = float(message.text.replace(',', '.'))
        if hold_balance < 0:
            raise ValueError

        data = await state.get_data()
        total_balance = data['total_balance']
        available_balance = data['available_balance']

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
            total_balance,
            available_balance,
            hold_balance,
            prices
        )

        await state.update_data(
            hold_balance=hold_balance,
            prices=prices,
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


@router.callback_query(F.data.startswith("payment_"))
async def process_payment_choice(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка выбора метода оплаты"""
    payment_method = callback.data.split("_")[1]  # rub, gram, stars

    data = await state.get_data()
    request_id = data['request_id']
    prices = data['prices']

    # Обновляем заявку
    await db.update_sale_request(request_id, payment_method=payment_method)

    # Отправляем заявку админу
    admin_text = f"""
🔔 <b>Новая заявка на продажу канала!</b>

👤 Пользователь: @{callback.from_user.username or 'unknown'}
🆔 ID: <code>{callback.from_user.id}</code>

📊 <b>Данные канала:</b>
💰 Общий баланс: {data['total_balance']} Stars
✅ Доступно: {data['available_balance']} Stars
🔒 В холде: {data['hold_balance']} Stars

💵 <b>Расчетная стоимость:</b>
🪙 {prices['stars']} Stars
💎 {prices['gram']} GRAM
💵 {prices['rub']} RUB

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
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

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
        request_id = int(callback.data.split(":")[1])
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
    payment_details = message.text

    data = await state.get_data()
    request_id = data.get('request_id')

    if not request_id:
        await message.answer(
            "❌ Произошла ошибка. Начните процесс заново.",
            reply_markup=main_menu_kb()
        )
        await state.clear()
        return

    # Обновляем заявку
    await db.update_sale_request(
        request_id,
        payment_details=payment_details,
        status='awaiting_payout'
    )

    # Получаем данные заявки
    request = await db.get_sale_request(request_id)

    # Отправляем админу заявку на выплату
    admin_text = f"""
💳 <b>Заявка на выплату</b>

👤 Пользователь: @{message.from_user.username or 'unknown'}
🆔 ID: <code>{message.from_user.id}</code>

💰 Сумма: {request['calculated_price_' + request['payment_method']]} {request['payment_method'].upper()}
💳 Метод: {request['payment_method'].upper()}

📝 <b>Реквизиты:</b>
<code>{payment_details}</code>

📋 ID заявки: <code>{request_id}</code>
"""

    from utils.keyboards import payment_action_kb

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=payment_action_kb(request_id)
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    # Уведомляем пользователя
    user_text = """
✅ <b>Реквизиты отправлены!</b>

Выплата поступит после передачи канала.
Ожидайте подтверждения от модератора.
"""

    await message.answer(user_text, reply_markup=main_menu_kb())
    await state.clear()
