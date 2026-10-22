"""Обработчики системы поддержки."""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import back_to_main_kb, main_menu_kb, support_menu_kb
from utils.validation import safe_html

router = Router()
db = Database()
logger = logging.getLogger(__name__)


class SupportStates(StatesGroup):
    waiting_message = State()


@router.message(F.text == "💬 Поддержка")
async def support_menu(message: Message):
    """Меню поддержки"""
    text = """
💬 <b>Поддержка</b>

Здесь вы можете задать вопрос или сообщить о проблеме.
Наша команда ответит вам в ближайшее время.

Выберите действие:
"""

    await message.answer(text, reply_markup=support_menu_kb())


@router.callback_query(F.data == "support_write")
async def start_support_ticket(callback: CallbackQuery, state: FSMContext):
    """Начало создания обращения"""
    text = """
✍️ <b>Создание обращения</b>

Опишите вашу проблему или вопрос.
Вы можете отправить текст, фото, видео или документ.

Ожидаем ваше сообщение:
"""

    await callback.message.edit_text(text, reply_markup=back_to_main_kb())
    await state.set_state(SupportStates.waiting_message)
    await callback.answer()


@router.message(SupportStates.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка сообщения в поддержку"""
    # Формируем текст обращения
    ticket_text = message.text or message.caption or "[Медиафайл без текста]"

    # Создаем тикет в базе
    ticket_id = await db.create_ticket(
        message.from_user.id,
        message.from_user.username or "unknown",
        ticket_text
    )

    # Отправляем админу
    admin_text = f"""
💬 <b>Новое обращение в поддержку</b>

👤 От: @{safe_html(message.from_user.username or 'unknown')}
🆔 ID: <code>{message.from_user.id}</code>
🎫 Тикет: <code>{ticket_id}</code>

📝 <b>Сообщение:</b>
{safe_html(ticket_text)}
"""

    from utils.keyboards import ticket_action_kb

    try:
        # Пересылаем сообщение админу как есть (с медиа если есть)
        if message.text:
            await bot.send_message(
                ADMIN_ID,
                admin_text,
                reply_markup=ticket_action_kb(ticket_id)
            )
        else:
            # Если есть медиа, пересылаем его
            await message.forward(ADMIN_ID)
            await bot.send_message(
                ADMIN_ID,
                admin_text,
                reply_markup=ticket_action_kb(ticket_id)
            )
    except Exception:
        logger.exception("Не удалось отправить тикет %s администратору", ticket_id)
        await message.answer(
            "❌ Не удалось передать обращение администратору. Попробуйте позже.",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    # Уведомляем пользователя
    user_text = f"""
✅ <b>Обращение отправлено!</b>

Ваше обращение принято и передано модератору.
Ожидайте ответа. Мы свяжемся с вами в ближайшее время.

🎫 Номер вашего обращения: <code>{ticket_id}</code>
"""

    await message.answer(user_text, reply_markup=main_menu_kb())
    await state.clear()
