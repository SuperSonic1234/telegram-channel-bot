"""
Обработчики для пользовательских команд
"""
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import main_menu_kb
from utils.validation import safe_html

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

    is_admin = message.from_user.id == ADMIN_ID

    await message.answer(
        welcome_msg,
        reply_markup=main_menu_kb(is_admin=is_admin)
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
👤 Username: @{safe_html(user['username'] or 'не указан')}
📊 Продано каналов: {user['channels_sold']}
💰 Заработано: {user['total_earned']:.2f} RUB
"""

    is_admin = message.from_user.id == ADMIN_ID

    await message.answer(profile_text, reply_markup=main_menu_kb(is_admin=is_admin))


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    welcome_msg = await db.get_setting('welcome_message')
    if not welcome_msg:
        welcome_msg = "Добро пожаловать в бот скупки каналов! 👋"

    is_admin = callback.from_user.id == ADMIN_ID

    await callback.message.edit_text(welcome_msg)
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_kb(is_admin=is_admin))
    await callback.answer()


@router.message(F.text == "🛠 Панель администратора")
async def admin_button(message: Message):
    """Обработка кнопки админ-панели"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой функции")
        return

    from admin.admin_handlers import show_admin_panel
    await show_admin_panel(message)
