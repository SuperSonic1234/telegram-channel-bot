"""
Обработчики для настроек бота
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import admin_settings_kb, back_to_admin_kb, rates_settings_kb
from utils.validation import parse_finite_number, safe_html

router = Router()
db = Database()


class SettingsStates(StatesGroup):
    waiting_welcome = State()
    waiting_commission = State()
    waiting_minimum_sale_balance = State()
    waiting_support_contact = State()
    waiting_gram_rate = State()
    waiting_stars_rate = State()
    waiting_withdrawal_fee = State()
    waiting_fragment_fee = State()


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

📊 Минимальный баланс для продажи: <code>{settings_dict.get('minimum_sale_balance', '0')} Stars</code>

📞 Контакт поддержки: <code>{safe_html(settings_dict.get('support_contact', '@support'))}</code>

💱 Курс GRAM к RUB: <code>{settings_dict.get('gram_to_rub_override') or 'автоматический'}</code>

⭐ Курс 1 Star к RUB: <code>{settings_dict.get('stars_to_rub_rate', '1')}</code>

💸 Комиссия вывода с канала: <code>{settings_dict.get('stars_withdrawal_commission', '5')}%</code>

💎 Комиссия Fragment: <code>{settings_dict.get('fragment_conversion_commission', '5')}%</code>

Выберите параметр для изменения:
"""

    await callback.message.edit_text(text, reply_markup=admin_settings_kb())
    await callback.answer()


@router.callback_query(F.data == "settings_rates")
async def show_rates_settings(callback: CallbackQuery):
    """Показать настройки курсов валют."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    gram_to_rub = await db.get_setting("gram_to_rub_override") or "автоматический"
    stars_to_rub = await db.get_setting("stars_to_rub_rate")
    if not stars_to_rub:
        legacy_stars_to_gram = await db.get_setting("stars_to_gram_rate") or "0.01"
        try:
            stars_to_rub = f"{float(gram_to_rub) * float(legacy_stars_to_gram):.6f}"
        except (TypeError, ValueError):
            stars_to_rub = "рассчитывается автоматически"

    try:
        star_to_gram = float(stars_to_rub) / float(gram_to_rub)
        star_to_gram_text = f"{star_to_gram:.8f}"
    except (TypeError, ValueError):
        star_to_gram_text = "рассчитывается автоматически"

    text = f"""
💱 <b>Курсы Stars / GRAM / RUB</b>

Текущие значения:
💵 1 GRAM = <code>{safe_html(gram_to_rub)}</code> RUB
💰 1 Star = <code>{safe_html(stars_to_rub)}</code> RUB
⭐ 1 Star = <code>{star_to_gram_text}</code> GRAM (расчётный)

Введите курсы вручную для точного расчёта стоимости канала.
"""

    await callback.message.edit_text(text, reply_markup=rates_settings_kb())
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


@router.callback_query(F.data == "settings_fragment_fee")
async def edit_fragment_fee(callback: CallbackQuery, state: FSMContext):
    """Изменить комиссию конвертации Fragment."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting("fragment_conversion_commission") or "5"
    text = f"""
💎 <b>Изменение комиссии Fragment</b>

Текущее значение: <code>{current}%</code>

Введите комиссию Fragment от 0 до 100 процентов.
"""
    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_fragment_fee)
    await callback.answer()


@router.message(SettingsStates.waiting_fragment_fee)
async def save_fragment_fee(message: Message, state: FSMContext):
    """Сохранить комиссию Fragment."""
    if not is_admin(message.from_user.id):
        return

    try:
        fee = parse_finite_number(message.text)
        if fee < 0 or fee > 100:
            raise ValueError
        await db.set_setting("fragment_conversion_commission", str(fee))
        await message.answer(
            f"✅ Комиссия Fragment обновлена: {fee}%",
            reply_markup=back_to_admin_kb(),
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число от 0 до 100.")


@router.callback_query(F.data == "settings_minimum_sale_balance")
async def edit_minimum_sale_balance(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('minimum_sale_balance') or '0'
    text = f"""
📊 <b>Минимальный баланс для продажи</b>

Текущее значение: <code>{current} Stars</code>

Введите минимальный общий баланс канала в Stars.
Введите <code>0</code>, чтобы отключить ограничение.
"""
    await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    await state.set_state(SettingsStates.waiting_minimum_sale_balance)
    await callback.answer()


@router.message(SettingsStates.waiting_minimum_sale_balance)
async def save_minimum_sale_balance(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        minimum_sale_balance = parse_finite_number(message.text)
        if minimum_sale_balance < 0:
            raise ValueError

        await db.set_setting('minimum_sale_balance', str(minimum_sale_balance))
        await message.answer(
            f"✅ Минимальный баланс для продажи обновлен: {minimum_sale_balance:g} Stars",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число не меньше 0.")

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
            reply_markup=rates_settings_kb(),
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
            reply_markup=rates_settings_kb()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное положительное число."
        )


@router.callback_query(F.data == "settings_stars_rate")
async def edit_stars_rate(callback: CallbackQuery, state: FSMContext):
    """Изменить курс Stars к RUB"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await db.get_setting('stars_to_rub_rate') or '1'

    text = f"""
⭐ <b>Изменение курса Stars к RUB</b>

Текущее значение: <code>1 Star = {current} RUB</code>

Введите стоимость одной звезды в рублях (например, 0.85):

<i>Этот курс напрямую используется для точного расчёта стоимости канала.</i>
"""

    await callback.message.edit_text(text, reply_markup=rates_settings_kb())
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

        await db.set_setting('stars_to_rub_rate', str(rate))

        await message.answer(
            f"✅ Курс Stars обновлен: 1 Star = {rate} RUB",
            reply_markup=rates_settings_kb()
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
