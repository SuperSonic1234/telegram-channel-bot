"""Администрирование реферальной системы и NFT-наград."""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import admin_referral_kb, back_to_admin_kb, referral_reward_kb
from utils.validation import parse_finite_number, safe_html

router = Router()
db = Database()


class ReferralAdminStates(StatesGroup):
    waiting_threshold = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def require_admin(callback: CallbackQuery) -> bool:
    if is_admin(callback.from_user.id):
        return True
    await callback.answer("❌ Нет доступа", show_alert=True)
    return False


async def referral_admin_text() -> tuple[str, bool]:
    enabled = (await db.get_setting("referral_enabled") or "1") == "1"
    threshold = await db.get_setting("referral_nft_threshold") or "5"
    rewards = await db.get_pending_referral_rewards()
    return (
        f"🎁 <b>Реферальная система</b>\n\n"
        f"Статус: <b>{'включена' if enabled else 'выключена'}</b>\n"
        f"NFT за приглашённых продавцов: <b>{threshold}</b>\n"
        f"Заявок на NFT ожидают: <b>{len(rewards)}</b>",
        enabled,
    )


@router.callback_query(F.data == "admin_referrals")
async def show_referrals_admin(callback: CallbackQuery):
    if not await require_admin(callback):
        return
    text, enabled = await referral_admin_text()
    await callback.message.edit_text(text, reply_markup=admin_referral_kb(enabled))
    await callback.answer()


@router.callback_query(F.data == "referral_toggle")
async def toggle_referrals(callback: CallbackQuery):
    if not await require_admin(callback):
        return
    enabled = (await db.get_setting("referral_enabled") or "1") == "1"
    await db.set_setting("referral_enabled", "0" if enabled else "1")
    text, current = await referral_admin_text()
    await callback.message.edit_text(text, reply_markup=admin_referral_kb(current))
    await callback.answer("Настройка обновлена")


@router.callback_query(F.data == "referral_threshold")
async def edit_referral_threshold(callback: CallbackQuery, state: FSMContext):
    if not await require_admin(callback):
        return
    current = await db.get_setting("referral_nft_threshold") or "5"
    await callback.message.edit_text(
        f"🎯 Текущий порог: <code>{current}</code>\n\nВведите количество приглашённых, продавших канал, для получения NFT:",
        reply_markup=back_to_admin_kb(),
    )
    await state.set_state(ReferralAdminStates.waiting_threshold)
    await callback.answer()


@router.message(ReferralAdminStates.waiting_threshold)
async def save_referral_threshold(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        threshold = parse_finite_number(message.text)
        if threshold < 1 or threshold != int(threshold):
            raise ValueError
        await db.set_setting("referral_nft_threshold", str(int(threshold)))
        await message.answer(f"✅ Порог NFT установлен: {int(threshold)} продаж", reply_markup=back_to_admin_kb())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите целое число больше нуля.")


@router.callback_query(F.data == "referral_stats")
async def referral_stats(callback: CallbackQuery):
    if not await require_admin(callback):
        return
    rows = await db.get_referral_leaderboard()
    text = "📊 <b>Статистика рефералов</b>\n\n"
    for row in rows[:30]:
        if row["invited_count"]:
            text += f"• @{safe_html(row['username'] or 'без username')} — приглашено: {row['invited_count']}, продали: {row['sold_count'] or 0}\n"
    await callback.message.edit_text(text or "📊 Статистика пока пуста.", reply_markup=back_to_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "referral_rewards")
async def referral_rewards(callback: CallbackQuery):
    if not await require_admin(callback):
        return
    rewards = await db.get_pending_referral_rewards()
    if not rewards:
        await callback.message.edit_text("📋 Заявок на NFT нет.", reply_markup=back_to_admin_kb())
    else:
        buttons = [[InlineKeyboardButton(text=f"#{r['id']} @{r['username'] or r['user_id']} — {r['sold_count']} продаж", callback_data=f"ref_reward_view:{r['id']}")] for r in rewards]
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_referrals")])
        await callback.message.edit_text("📋 <b>Заявки на NFT</b>\n\nВыберите заявку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("ref_reward_view:"))
async def view_referral_reward(callback: CallbackQuery):
    if not await require_admin(callback):
        return
    reward_id = int(callback.data.split(":", 1)[1])
    reward = await db.get_referral_reward(reward_id)
    if not reward:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    sold = await db.get_sold_referrals(reward["user_id"])
    sales = "\n".join(f"• @{safe_html(item['username'] or 'без username')} — {item['sale_amount']} {item['sale_currency'].upper()}" for item in sold) or "нет данных"
    text = f"🎁 <b>Заявка на NFT #{reward['id']}</b>\n\n👤 Ник: @{safe_html(reward['username'] or 'без username')}\n🆔 ID: <code>{reward['user_id']}</code>\n👥 Приглашено: <b>{reward['invited_count']}</b>\n✅ Продали канал: <b>{reward['sold_count']}</b>\n\n<b>Продажи рефералов:</b>\n{sales}"
    await callback.message.edit_text(text, reply_markup=referral_reward_kb(reward_id))
    await callback.answer()


async def process_reward(callback: CallbackQuery, bot: Bot, status: str):
    if not await require_admin(callback):
        return
    reward_id = int(callback.data.split(":", 1)[1])
    reward = await db.get_referral_reward(reward_id)
    if not reward or not await db.process_referral_reward(reward_id, status, "Условия не выполнены" if status == "rejected" else None):
        await callback.answer("❌ Заявка уже обработана", show_alert=True)
        return
    message = "🎁 Ваш подарок отправлен на ваш аккаунт!" if status == "sent" else "❌ В выдаче NFT отказано: условия не выполнены."
    try:
        await bot.send_message(reward["user_id"], message)
    except Exception:
        pass
    await callback.message.edit_text("✅ Награда обработана.", reply_markup=back_to_admin_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("ref_reward_send:"))
async def send_referral_reward(callback: CallbackQuery, bot: Bot):
    await process_reward(callback, bot, "sent")


@router.callback_query(F.data.startswith("ref_reward_reject:"))
async def reject_referral_reward(callback: CallbackQuery, bot: Bot):
    await process_reward(callback, bot, "rejected")
