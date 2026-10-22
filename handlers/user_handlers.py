"""
Обработчики для пользовательских команд
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from utils.keyboards import main_menu_kb, back_to_main_kb

router = Router()
db = Database()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()

    # Добавляем пользователя в базу
    await db.add_user(message.from_user.id, message.from_user.username)

    # Получаем приветственное сообщение из настроек
    welcome_msg = await db.get_setting('welcome_message')
    if not welcome_msg:
        welcome_msg = "Добро пожаловать в бот скупки каналов! 👋"

    await message.answer(
        welcome_msg,
        reply_markup=main_menu_kb()
    )


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    """Показать профиль пользователя"""
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("Произошла ошибка. Используйте /start")
        return

    profile_text = f"""
👤 <b>Ваш профиль</b>

🆔 ID: <code>{user['user_id']}</code>
👤 Username: @{user['username'] or 'не указан'}
📊 Продано каналов: {user['channels_sold']}
💰 Заработано: {user['total_earned']:.2f} RUB
"""

    await message.answer(profile_text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    welcome_msg = await db.get_setting('welcome_message')
    if not welcome_msg:
        welcome_msg = "Добро пожаловать в бот скупки каналов! 👋"

    await callback.message.edit_text(welcome_msg)
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_kb())
    await callback.answer()
