"""
Обработчики для пользовательских команд
"""
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import main_menu_inline_kb, main_menu_kb, referral_kb
from utils.validation import safe_html

router = Router()
db = Database()


async def send_welcome(target: Message, bot: Bot, is_admin: bool) -> None:
    source_chat_id = await db.get_setting("welcome_message_chat_id")
    source_message_id = await db.get_setting("welcome_message_id")
    if source_chat_id and source_message_id:
        try:
            await bot.copy_message(
                chat_id=target.chat.id,
                from_chat_id=int(source_chat_id),
                message_id=int(source_message_id),
                reply_markup=main_menu_inline_kb(),
            )
            if is_admin:
                await target.answer("\u2063", reply_markup=main_menu_kb(is_admin=True))
            return
        except Exception:
            pass
    welcome_msg = await db.get_setting("welcome_message") or "Добро пожаловать в бот скупки каналов! 👋"
    await target.answer(welcome_msg, reply_markup=main_menu_inline_kb())
    if is_admin:
        await target.answer("\u2063", reply_markup=main_menu_kb(is_admin=True))

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Обработка команды /start"""
    await state.clear()

    # Добавляем пользователя в базу
    await db.add_user(message.from_user.id, message.from_user.username)
    payload = (message.text or "").split(maxsplit=1)
    if len(payload) == 2 and payload[1].startswith("ref_"):
        try:
            referrer_id = int(payload[1][4:])
        except ValueError:
            referrer_id = None
        if referrer_id and await db.register_referral(referrer_id, message.from_user.id):
            await bot.send_message(
                referrer_id,
                f"🎉 По вашей ссылке зарегистрировался новый пользователь!\n"
                f"👤 @{safe_html(message.from_user.username or 'без username')}",
            )

    is_admin = message.from_user.id == ADMIN_ID
    await send_welcome(message, bot, is_admin)


@router.message(F.text == "🎁 Реферальная система")
async def show_referrals(message: Message, bot: Bot):
    stats = await db.get_referral_stats(message.from_user.id)
    bot_user = await bot.get_me()
    referral_link = f"https://t.me/{bot_user.username}?start=ref_{message.from_user.id}"
    enabled_text = "включена" if stats["enabled"] else "временно отключена"
    remaining = max(stats["threshold"] - (stats["sold"] % stats["threshold"]), 0)
    text = f"""
🎁 <b>Реферальная система</b>

Статус: <b>{enabled_text}</b>
Ваша ссылка:
<code>{referral_link}</code>

👥 Приглашено: <b>{stats['invited']}</b>
✅ Продали канал: <b>{stats['sold']}</b>
🎯 До следующего NFT: <b>{remaining}</b>

Условия: за каждые <b>{stats['threshold']}</b> приглашённых пользователей, которые продадут канал, вы получаете NFT.
"""
    await message.answer(text, reply_markup=referral_kb(stats["can_claim"]))



@router.callback_query(F.data == "main_referrals")
async def main_referrals_callback(callback: CallbackQuery, bot: Bot):
    await show_referrals(callback.message, bot)
    await callback.answer()


@router.callback_query(F.data == "main_profile")
async def main_profile_callback(callback: CallbackQuery):
    await show_profile(callback.message)
    await callback.answer()

@router.callback_query(F.data == "referral_claim")
async def claim_referral_reward(callback: CallbackQuery, bot: Bot):
    reward = await db.request_referral_reward(callback.from_user.id)
    if not reward:
        await callback.answer("❌ Условия для получения NFT ещё не выполнены", show_alert=True)
        return
    sold = await db.get_sold_referrals(callback.from_user.id)
    sold_text = "\n".join(
        f"• @{safe_html(item['username'] or 'без username')} — "
        f"{item['sale_amount']} {item['sale_currency'].upper()}"
        for item in sold
    ) or "нет данных"
    await bot.send_message(
        ADMIN_ID,
        f"🎁 <b>Новая заявка на NFT</b>\n\n"
        f"👤 Ник: @{safe_html(callback.from_user.username or 'без username')}\n"
        f"🆔 ID: <code>{callback.from_user.id}</code>\n"
        f"👥 Приглашено: {reward['invited_count']}\n"
        f"✅ Продали канал: {reward['sold_count']}\n\n"
        f"<b>Продажи рефералов:</b>\n{sold_text}",
    )
    await callback.message.edit_text("✅ Заявка на NFT отправлена администратору. Ожидайте решения.")
    await callback.answer()


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

    await message.answer(profile_text, reply_markup=main_menu_inline_kb())


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Возврат в главное меню"""
    await state.clear()

    is_admin = callback.from_user.id == ADMIN_ID
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_welcome(callback.message, bot, is_admin)
    await callback.answer()


@router.message(F.text == "🛠 Панель администратора")
async def admin_button(message: Message):
    """Обработка кнопки админ-панели"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой функции")
        return

    from admin.admin_handlers import show_admin_panel
    await show_admin_panel(message)
