"""
Основные обработчики админ-панели
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import Database
from utils.keyboards import (
    admin_panel_kb, admin_history_kb, back_to_admin_kb,
    confirm_broadcast_kb, ticket_action_kb
)
from utils.calculator import ChannelPriceCalculator

router = Router()
db = Database()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_ticket_reply = State()
    waiting_calculator_amount = State()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == ADMIN_ID


async def show_admin_panel(message: Message):
    """Показать админ-панель (для вызова из обработчика кнопки)"""
    text = """
⚙️ <b>Админ-панель</b>

Добро пожаловать в панель управления ботом.
Выберите нужный раздел:
"""

    await message.answer(text, reply_markup=admin_panel_kb())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Открыть админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    await show_admin_panel(message)


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel_callback(callback: CallbackQuery):
    """Показать админ-панель (из callback)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    text = """
⚙️ <b>Админ-панель</b>

Добро пожаловать в панель управления ботом.
Выберите нужный раздел:
"""

    await callback.message.edit_text(text, reply_markup=admin_panel_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery):
    """Показать список пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    users = await db.get_all_users()

    text = "👥 <b>Список пользователей</b>\n\n"

    if not users:
        text += "Пользователей пока нет."
    else:
        for user in users[:50]:  # Показываем первых 50
            username = f"@{user['username']}" if user['username'] else "без username"
            text += f"• {username} (ID: <code>{user['user_id']}</code>)\n"
            text += f"  Продано: {user['channels_sold']} | Заработано: {user['total_earned']:.2f} RUB\n\n"

        if len(users) > 50:
            text += f"\n... и еще {len(users) - 50} пользователей"

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def show_statistics(callback: CallbackQuery):
    """Показать статистику бота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    stats = await db.get_statistics()

    text = f"""
📊 <b>Статистика бота</b>

👥 Всего пользователей: {stats['total_users']}
📋 Всего заявок: {stats['total_requests']}
✅ Одобрено заявок: {stats['approved_requests']}
💰 Всего заработано: {stats['total_earned']:.2f} RUB

📈 Конверсия: {(stats['approved_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0:.1f}%
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    text = """
📢 <b>Рассылка сообщений</b>

Отправьте сообщение, которое хотите разослать всем пользователям.
Поддерживается текст, фото, видео и другие медиафайлы.

Ожидаю сообщение для рассылки:
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    """Обработка рассылки"""
    if not is_admin(message.from_user.id):
        return

    # Сохраняем сообщение для рассылки
    await state.update_data(
        broadcast_text=message.text or message.caption,
        broadcast_message_id=message.message_id
    )

    text = """
📢 <b>Подтверждение рассылки</b>

Вы уверены, что хотите отправить это сообщение всем пользователям?

Предпросмотр сообщения выше ⬆️
"""

    await message.answer(text, reply_markup=confirm_broadcast_kb())


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и выполнение рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    message_id = data.get('broadcast_message_id')

    users = await db.get_all_users()

    await callback.message.edit_text("📤 Рассылка началась...")

    success = 0
    failed = 0

    for user in users:
        try:
            # Пересылаем сообщение пользователю
            await bot.copy_message(
                chat_id=user['user_id'],
                from_chat_id=callback.from_user.id,
                message_id=message_id
            )
            success += 1
        except Exception as e:
            failed += 1
            print(f"Не удалось отправить пользователю {user['user_id']}: {e}")

    result_text = f"""
✅ <b>Рассылка завершена!</b>

Успешно: {success}
Не удалось: {failed}
"""

    await callback.message.edit_text(result_text, reply_markup=back_to_admin_kb())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_history")
async def show_history_menu(callback: CallbackQuery):
    """Показать меню истории скупки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    text = """
📜 <b>История скупки каналов</b>

Выберите категорию для просмотра:
"""

    await callback.message.edit_text(text, reply_markup=admin_history_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_bought")
async def show_bought_channels(callback: CallbackQuery):
    """Показать купленные каналы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    channels = await db.get_purchased_channels()

    text = "✅ <b>Купленные каналы</b>\n\n"

    if not channels:
        text += "Пока нет купленных каналов."
    else:
        for ch in channels[:30]:
            text += f"• @{ch['username']}\n"
            text += f"  Канал: {ch['channel_username'] or 'N/A'}\n"
            text += f"  Цена: {ch['price']} {ch['currency'].upper()}\n"
            text += f"  Дата: {ch['purchase_date']}\n\n"

        if len(channels) > 30:
            text += f"\n... и еще {len(channels) - 30} каналов"

    await callback.message.edit_text(text, reply_markup=admin_history_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_rejected")
async def show_rejected_channels(callback: CallbackQuery):
    """Показать отказанные каналы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    channels = await db.get_rejected_channels()

    text = "❌ <b>Отказанные каналы</b>\n\n"

    if not channels:
        text += "Нет отказанных заявок."
    else:
        for ch in channels[:30]:
            text += f"• @{ch['username']}\n"
            text += f"  Канал: {ch['channel_username'] or 'N/A'}\n"
            text += f"  Цена: {ch['price']} {ch['currency'].upper()}\n"
            text += f"  Дата: {ch['purchase_date']}\n\n"

        if len(channels) > 30:
            text += f"\n... и еще {len(channels) - 30} каналов"

    await callback.message.edit_text(text, reply_markup=admin_history_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_support")
async def show_support_tickets(callback: CallbackQuery):
    """Показать обращения в поддержку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    tickets = await db.get_open_tickets()

    text = "💬 <b>Обращения в поддержку</b>\n\n"

    if not tickets:
        text += "Нет открытых обращений."
    else:
        for ticket in tickets[:20]:
            text += f"🎫 Тикет #{ticket['id']}\n"
            text += f"👤 @{ticket['username']} (ID: <code>{ticket['user_id']}</code>)\n"
            text += f"📝 {ticket['message'][:100]}...\n"
            text += f"📅 {ticket['created_at']}\n\n"

            # Добавляем кнопку для ответа
            # Но через текст это неудобно, поэтому лучше использовать инлайн-кнопки

        if len(tickets) > 20:
            text += f"\n... и еще {len(tickets) - 20} обращений"

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_reply:"))
async def start_ticket_reply(callback: CallbackQuery, state: FSMContext):
    """Начать ответ на обращение"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[1])

    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminStates.waiting_ticket_reply)

    text = """
✍️ <b>Ответ на обращение</b>

Напишите ваш ответ пользователю:
"""

    await callback.message.edit_text(text)
    await callback.answer()


@router.message(AdminStates.waiting_ticket_reply)
async def process_ticket_reply(message: Message, state: FSMContext, bot: Bot):
    """Обработка ответа на обращение"""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    ticket_id = data.get('ticket_id')

    # Получаем данные тикета
    async with db.db_path as conn:
        async with conn.execute(
            "SELECT user_id, username FROM support_tickets WHERE id = ?",
            (ticket_id,)
        ) as cursor:
            ticket = await cursor.fetchone()

    if not ticket:
        await message.answer("❌ Тикет не найден.")
        await state.clear()
        return

    user_id = ticket[0]

    # Отправляем ответ пользователю
    user_text = f"""
💬 <b>Ответ от поддержки</b>

{message.text}

Ваше обращение #{ticket_id} закрыто.
Если у вас остались вопросы, создайте новое обращение.
"""

    try:
        await bot.send_message(user_id, user_text)
        await message.answer("✅ Ответ отправлен пользователю!")

        # Закрываем тикет
        await db.close_ticket(ticket_id)

    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()


@router.callback_query(F.data == "admin_calculator")
async def show_calculator(callback: CallbackQuery, state: FSMContext):
    """Показать калькулятор для расчета стоимости"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    text = """
🧮 <b>Калькулятор стоимости канала</b>

Отправьте количество звезд (Stars) в канале, и я рассчитаю, сколько вы получите после вывода.

<i>Например: 10000</i>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.waiting_calculator_amount)
    await callback.answer()


@router.message(AdminStates.waiting_calculator_amount)
async def process_calculator(message: Message, state: FSMContext):
    """Обработка расчета калькулятора"""
    if not is_admin(message.from_user.id):
        return

    try:
        stars_amount = float(message.text.replace(',', '.').replace(' ', ''))

        if stars_amount <= 0:
            await message.answer("❌ Количество звезд должно быть больше нуля. Попробуйте еще раз:")
            return

        # Показываем что идет расчет
        calc_msg = await message.answer("⏳ Получаем актуальный курс TON и производим расчет...")

        # Используем новый калькулятор с актуальными курсами
        calculation = await ChannelPriceCalculator.calculate_net_amount(stars_amount)

        # Удаляем сообщение о расчете
        await calc_msg.delete()

        # Показываем результат
        result_text = ChannelPriceCalculator.format_calculator_message(calculation)
        await message.answer(result_text, reply_markup=admin_panel_kb())

        await state.clear()

    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (например: 10000):")
    except Exception as e:
        await message.answer(f"❌ Ошибка расчета: {e}")
        await state.clear()

