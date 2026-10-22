"""
Обработчики для настроек бота
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import admin_settings_kb, back_to_admin_kb
from utils.validation import parse_finite_number, safe_html

router = Router()
db = Database()


class SettingsStates(StatesGroup):
    waiting_welcome = State()
    waiting_commission = State()
    waiting_support_contact = State()
    waiting_gram_rate = State()
    waiting_stars_rate = State()
    waiting_withdrawal_fee = State()


def is_admin(user_id: int) -> bool:
    """Проверка администратора"""
    return user_id == ADMIN_ID


@router.callback_query(F.data == "admin_settings")
async def show_settings(callback: CallbackQuery):
    """Показать настройки бота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    # Получаем текущие настройки
    settings = await db.get_all_settings()

    settings_dict = {s['key']: s['value'] for s in settings}

    text = f"""
⚙️ <b>Настройки бота</b>

<b>Текущие значения:</b>

💬 Приветственное сообщение:
<code>{safe_html(settings_dict.get('welcome_message', 'Не установлено'))}</code>

💰 Процент комиссии: <code>{settings_dict.get('commission_percent', '30')}%</code>

📞 Контакт поддержки: <code>{safe_html(settings_dict.get('support_contact', '@support'))}</code>

💱 Курс GRAM к RUB: <code>{settings_dict.get('gram_to_rub_override') or 'автоматический'}</code>

⭐ Курс Stars к GRAM: <code>{settings_dict.get('stars_to_gram_rate', '0.01')}</code>

💸 Комиссия вывода звезд: <code>{settings_dict.get('stars_withdrawal_commission', '5')}%</code>

Выберите параметр для изменения:
"""

    await callback.message.edit_text(text, reply_markup=admin_settings_kb())
    await callback.answer()


@router.callback_query(F.data == "settings_welcome")
async def edit_welcome_message(callback: CallbackQuery, state: FSMContext):
    """Изменить приветственное сообщение"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    text = """
💬 <b>Изменение приветственного сообщения</b>

Отправьте новое приветственное сообщение.
Поддерживается HTML-форматирование.

<i>Пример:</i>
<code>Добро пожаловать в бот скупки каналов! 👋

Здесь вы можете выгодно продать свой канал.</code>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_welcome)
    await callback.answer()


@router.message(SettingsStates.waiting_welcome)
async def save_welcome_message(message: Message, state: FSMContext):
    """Сохранить приветственное сообщение"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение.")
        return
    await db.set_setting('welcome_message', message.text)

    await message.answer(
        "✅ Приветственное сообщение обновлено!",
        reply_markup=back_to_admin_kb()
    )
    await state.clear()


@router.callback_query(F.data == "settings_commission")
async def edit_commission(callback: CallbackQuery, state: FSMContext):
    """Изменить процент комиссии"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('commission_percent') or '30'

    text = f"""
💰 <b>Изменение процента комиссии</b>

Текущее значение: <code>{current}%</code>

Введите новый процент комиссии (число от 0 до 100):

<i>Этот процент вычитается из итоговой суммы как прибыль.</i>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_commission)
    await callback.answer()


@router.message(SettingsStates.waiting_commission)
async def save_commission(message: Message, state: FSMContext):
    """Сохранить процент комиссии"""
    if not is_admin(message.from_user.id):
        return

    try:
        commission = parse_finite_number(message.text)
        if commission < 0 or commission > 100:
            raise ValueError

        await db.set_setting('commission_percent', str(commission))

        await message.answer(
            f"✅ Процент комиссии обновлен: {commission}%",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число от 0 до 100."
        )


@router.callback_query(F.data == "settings_support_contact")
async def edit_support_contact(callback: CallbackQuery, state: FSMContext):
    """Изменить контакт поддержки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('support_contact') or '@support'

    text = f"""
📞 <b>Изменение контакта поддержки</b>

Текущее значение: <code>{current}</code>

Введите новый контакт поддержки (например, @username):

<i>Этот контакт будет показываться пользователям при отказе в покупке.</i>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_support_contact)
    await callback.answer()


@router.message(SettingsStates.waiting_support_contact)
async def save_support_contact(message: Message, state: FSMContext):
    """Сохранить контакт поддержки"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте контакт текстом.")
        return
    await db.set_setting('support_contact', message.text.strip())

    await message.answer(
        f"✅ Контакт поддержки обновлен: {safe_html(message.text.strip())}",
        reply_markup=back_to_admin_kb()
    )
    await state.clear()


@router.callback_query(F.data == "settings_gram_rate")
async def edit_gram_rate(callback: CallbackQuery, state: FSMContext):
    """Изменить курс GRAM к RUB"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('gram_to_rub_override') or 'автоматический курс'

    text = f"""
💱 <b>Изменение курса GRAM к RUB</b>

Текущее значение: <code>1 GRAM = {current} RUB</code>

Введите новый курс (например, 95.5) или слово <code>авто</code>, чтобы использовать рыночный курс:

<i>Этот курс используется для конвертации GRAM в рубли при расчете стоимости.</i>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_gram_rate)
    await callback.answer()


@router.message(SettingsStates.waiting_gram_rate)
async def save_gram_rate(message: Message, state: FSMContext):
    """Сохранить курс GRAM"""
    if not is_admin(message.from_user.id):
        return

    if message.text and message.text.strip().lower() in {"авто", "auto"}:
        await db.set_setting('gram_to_rub_override', '')
        await message.answer(
            "✅ Включен автоматический курс TON/RUB.",
            reply_markup=back_to_admin_kb(),
        )
        await state.clear()
        return

    try:
        rate = parse_finite_number(message.text)
        if rate <= 0:
            raise ValueError

        await db.set_setting('gram_to_rub_override', str(rate))

        await message.answer(
            f"✅ Курс GRAM обновлен: 1 GRAM = {rate} RUB",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное положительное число."
        )


@router.callback_query(F.data == "settings_stars_rate")
async def edit_stars_rate(callback: CallbackQuery, state: FSMContext):
    """Изменить курс Stars к GRAM"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('stars_to_gram_rate') or '0.01'

    text = f"""
⭐ <b>Изменение курса Stars к GRAM</b>

Текущее значение: <code>1 Star = {current} GRAM</code>

Введите новый курс (например, 0.012):

<i>Этот курс используется для конвертации звезд в GRAM при расчете стоимости.</i>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_stars_rate)
    await callback.answer()


@router.message(SettingsStates.waiting_stars_rate)
async def save_stars_rate(message: Message, state: FSMContext):
    """Сохранить курс Stars"""
    if not is_admin(message.from_user.id):
        return

    try:
        rate = parse_finite_number(message.text)
        if rate <= 0:
            raise ValueError

        await db.set_setting('stars_to_gram_rate', str(rate))

        await message.answer(
            f"✅ Курс Stars обновлен: 1 Star = {rate} GRAM",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное положительное число."
        )


@router.callback_query(F.data == "settings_withdrawal_fee")
async def edit_withdrawal_fee(callback: CallbackQuery, state: FSMContext):
    """Изменить комиссию вывода звезд"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('stars_withdrawal_commission') or '5'

    text = f"""
💸 <b>Изменение комиссии вывода звезд</b>

Текущее значение: <code>{current}%</code>

Введите новую комиссию (число от 0 до 100):

<i>Эта комиссия вычитается при выводе звезд с канала на кошелек.</i>
"""

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_withdrawal_fee)
    await callback.answer()


@router.message(SettingsStates.waiting_withdrawal_fee)
async def save_withdrawal_fee(message: Message, state: FSMContext):
    """Сохранить комиссию вывода"""
    if not is_admin(message.from_user.id):
        return

    try:
        fee = parse_finite_number(message.text)
        if fee < 0 or fee > 100:
            raise ValueError

        await db.set_setting('stars_withdrawal_commission', str(fee))

        await message.answer(
            f"✅ Комиссия вывода обновлена: {fee}%",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число от 0 до 100."
        )
