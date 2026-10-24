"""Администрирование заявок и выплат."""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_ID
from database import Database
from utils.keyboards import (
    back_to_admin_kb,
    payment_action_kb,
    payout_reject_reason_kb,
    reject_reason_kb,
    request_action_kb,
    request_archive_kb,
    send_payment_details_kb,
)
from utils.validation import safe_html

router = Router()
db = Database()
logger = logging.getLogger(__name__)


class RequestSearchStates(StatesGroup):
    waiting_request_id = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def _callback_id(data: str, position: int = -1) -> int | None:
    try:
        return int(data.split(":")[position])
    except (IndexError, TypeError, ValueError):
        return None


async def _require_admin(callback: CallbackQuery) -> bool:
    if is_admin(callback.from_user.id):
        return True
    await callback.answer("❌ Нет доступа", show_alert=True)
    return False


@router.callback_query(F.data == "admin_requests")
async def show_requests(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    requests = await db.get_pending_requests()
    text = "📋 <b>Заявки на рассмотрении</b>\n\n"
    if not requests:
        await callback.message.edit_text(text + "Нет ожидающих заявок.", reply_markup=back_to_admin_kb())
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"#{req['id']} - @{req['username']} - {req['calculated_price_rub']} RUB",
                    callback_data=f"view_request:{req['id']}",
                )
            ]
            for req in requests[:10]
        ]
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        await callback.message.edit_text(
            text + f"Всего заявок: {len(requests)}\n\n<i>Выберите заявку:</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_archive")
async def show_archive(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    requests = await db.get_all_sale_requests()
    text = "🗂 <b>Архив всех заявок</b>\n\n"
    if not requests:
        text += "Заявок пока нет."
        await callback.message.edit_text(text, reply_markup=back_to_admin_kb())
    else:
        keyboard = [
            [InlineKeyboardButton(
                text=f"#{request['id']} · {request['status']} · {request['calculated_price_rub']} RUB",
                callback_data=f"view_request:{request['id']}",
            )]
            for request in requests[:30]
        ]
        keyboard.insert(0, [InlineKeyboardButton(text="🔎 Найти по номеру", callback_data="search_request")])
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        await callback.message.edit_text(
            text + f"Всего заявок: {len(requests)}\n<i>Последние 30:</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    await callback.answer()


@router.callback_query(F.data == "search_request")
async def search_request(callback: CallbackQuery, state: FSMContext):
    if not await _require_admin(callback):
        return
    await callback.message.edit_text("🔎 Введите номер заявки:", reply_markup=back_to_admin_kb())
    await state.set_state(RequestSearchStates.waiting_request_id)
    await callback.answer()


@router.message(RequestSearchStates.waiting_request_id)
async def process_request_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        request_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введите целый номер заявки, например: 123")
        return
    request = await db.get_sale_request(request_id)
    await state.clear()
    if not request:
        await message.answer("❌ Заявка с таким номером не найдена.", reply_markup=back_to_admin_kb())
        return
    payment = await db.get_payment_by_request(request_id)
    text = (
        f"📋 <b>Заявка #{request_id}</b>\n\n"
        f"👤 @{safe_html(request['username'] or 'unknown')} (<code>{request['user_id']}</code>)\n"
        f"🔗 {safe_html(request['channel_link'] or 'не указан')}\n"
        f"📌 Статус: <code>{safe_html(request['status'])}</code>\n"
        f"💰 Баланс: {request['total_balance']} Stars\n"
        f"💵 Стоимость: {request['calculated_price_rub']} RUB / "
        f"{request['calculated_price_gram']} GRAM / {request['calculated_price_stars']} Stars\n"
        f"📅 Создана: {request['created_at']}\n"
    )
    if payment:
        text += (
            f"\n💳 Выплата: {payment['amount']} {payment['currency'].upper()}\n"
            f"📍 Статус: <code>{safe_html(payment['status'])}</code>\n"
            f"📝 Реквизиты:\n<code>{safe_html(payment['payment_details'] or '')}</code>"
        )
    await message.answer(text, reply_markup=back_to_admin_kb())


@router.callback_query(F.data.startswith("view_request:"))
async def view_request_details(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    request_id = _callback_id(callback.data)
    request = await db.get_sale_request(request_id) if request_id else None
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    channel = safe_html(request["channel_link"] or "не указан")
    username = safe_html(request["username"] or "unknown")
    payment_method = request["payment_method"].upper() if request["payment_method"] else "не выбрано"
    payment = await db.get_payment_by_request(request_id)
    events = await db.get_request_events(request_id)
    text = f"""
📋 <b>Заявка #{request['id']}</b>

👤 <b>Пользователь:</b> @{username}
🆔 <b>ID:</b> <code>{request['user_id']}</code>
🔗 <b>Канал:</b> {channel}

💰 <b>Баланс канала:</b>
• Общий: {request['total_balance']} Stars
• Доступно: {request['available_balance']} Stars
• В холде: {request['hold_balance']} Stars

💵 <b>Стоимость:</b>
• RUB: {request['calculated_price_rub']}
• GRAM: {request['calculated_price_gram']}
• Stars: {request['calculated_price_stars']}

💳 <b>Метод оплаты:</b> {payment_method}
📅 <b>Создана:</b> {request['created_at']}
📌 <b>Статус:</b> <code>{safe_html(request['status'])}</code>
🕒 <b>Обновлена:</b> {request['updated_at']}
"""
    if payment:
        text += (
            f"\n💳 <b>Выплата:</b> {payment['amount']} {payment['currency'].upper()}"
            f"\n📍 <b>Статус выплаты:</b> <code>{safe_html(payment['status'])}</code>"
            f"\n📝 <b>Реквизиты:</b>\n<code>{safe_html(payment['payment_details'] or '')}</code>"
        )
        if payment["paid_at"]:
            text += f"\n✅ <b>Выплачено:</b> {payment['paid_at']}"
        if payment["rejection_reason"]:
            text += f"\n❌ <b>Причина отказа:</b> {safe_html(payment['rejection_reason'])}"
    if events:
        text += "\n\n🧾 <b>История:</b>"
        for event in events[-10:]:
            transition = f" {event['old_status']} → {event['new_status']}" if event['new_status'] else ""
            text += f"\n• {event['created_at']} — {safe_html(event['event_type'])}{safe_html(transition)}"
    if request["status"] in {"pending", "approved"}:
        keyboard = request_action_kb(request_id)
    elif request["status"] == "awaiting_payout":
        keyboard = payment_action_kb(request_id)
    else:
        keyboard = request_archive_kb()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("approve_request:"))
async def approve_request(callback: CallbackQuery, bot: Bot):
    if not await _require_admin(callback):
        return
    request_id = _callback_id(callback.data)
    request = await db.get_sale_request(request_id) if request_id else None
    if not request or not request["payment_method"]:
        await callback.answer("❌ Заявка не найдена или метод оплаты не выбран", show_alert=True)
        return
    if not await db.transition_sale_request(request_id, "approved", ("pending",)):
        await callback.answer("❌ Заявка уже обработана", show_alert=True)
        return

    support_contact = await db.get_setting("support_contact") or "@support"
    amount = request[f"calculated_price_{request['payment_method']}"]
    user_text = f"""
✅ <b>Ваша заявка одобрена!</b>

Мы готовы купить ваш канал за:
💵 <b>{amount} {request['payment_method'].upper()}</b>

1️⃣ Передайте права администратора канала на контакт: {safe_html(support_contact)}
⏱ У вас есть 24 часа на передачу канала.

2️⃣ После передачи прав отправьте реквизиты кнопкой ниже.

⚠️ Выплата производится после подтверждения передачи канала.
"""
    try:
        await bot.send_message(
            request["user_id"], user_text, reply_markup=send_payment_details_kb(request_id)
        )
        await db.add_purchase(
            request_id,
            request["user_id"],
            request["username"],
            request["channel_link"] or "N/A",
            amount,
            request["payment_method"],
            "approved",
        )
    except Exception as exc:
        await db.transition_sale_request(request_id, "pending", ("approved",))
        logger.exception("Ошибка одобрения заявки %s", request_id)
        await callback.answer(f"❌ Не удалось уведомить пользователя: {exc}", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Заявка #{request_id} одобрена. Пользователь уведомлен.",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer("✅ Заявка одобрена")


@router.callback_query(F.data.startswith("reject_request:"))
async def show_reject_reasons(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    request_id = _callback_id(callback.data)
    if not request_id:
        await callback.answer("❌ Некорректная заявка", show_alert=True)
        return
    await callback.message.edit_text(
        "❌ <b>Отказ в покупке канала</b>\n\nВыберите причину:",
        reply_markup=reject_reason_kb(request_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reject_reason:"))
async def reject_request(callback: CallbackQuery, bot: Bot):
    if not await _require_admin(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Некорректная команда", show_alert=True)
        return
    reason_key, request_id = parts[1], _callback_id(callback.data)
    request = await db.get_sale_request(request_id) if request_id else None
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    reasons = {
        "not_transferred": "Вы не передали канал в указанные сроки.",
        "wrong_data": "Указанные данные не соответствуют действительности.",
        "blocked": "Канал заблокирован или имеет ограничения.",
    }
    reason_text = reasons.get(reason_key)
    if not reason_text:
        await callback.answer("❌ Неизвестная причина", show_alert=True)
        return
    if not await db.transition_sale_request(request_id, "rejected", ("pending", "approved")):
        await callback.answer("❌ Заявка уже обработана", show_alert=True)
        return
    await db.update_sale_request(request_id, rejection_reason=reason_text)

    support_contact = await db.get_setting("support_contact") or "@support"
    await db.add_purchase(
        request_id,
        request["user_id"],
        request["username"],
        request["channel_link"] or "N/A",
        request[f"calculated_price_{request['payment_method']}"] if request["payment_method"] else 0,
        request["payment_method"] or "N/A",
        "rejected",
    )
    try:
        await bot.send_message(
            request["user_id"],
            f"❌ <b>В покупке канала отказано</b>\n\n"
            f"<b>Причина:</b> {reason_text}\n\n"
            f"Если вы не согласны, свяжитесь с {safe_html(support_contact)}\n"
            f"📋 Номер заявки: <code>{request_id}</code>",
        )
    except Exception:
        logger.exception("Не удалось уведомить об отказе по заявке %s", request_id)

    await callback.message.edit_text(
        f"❌ Заявка #{request_id} отклонена.\nПричина: {reason_text}",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("payout_done:"))
async def payout_completed(callback: CallbackQuery, bot: Bot):
    if not await _require_admin(callback):
        return
    request_id = _callback_id(callback.data)
    request = await db.get_sale_request(request_id) if request_id else None
    if not request or not request["payment_method"]:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    if not await db.complete_payout(request_id):
        await callback.answer("❌ Выплата уже обработана или еще не готова", show_alert=True)
        return

    amount = request[f"calculated_price_{request['payment_method']}"]
    notification_error = False
    try:
        await bot.send_message(
            request["user_id"],
            f"✅ <b>Выплата отправлена!</b>\n\n"
            f"Выплата <b>{amount} {request['payment_method'].upper()}</b> успешно отправлена.\n\n"
            "Спасибо за сотрудничество! 🤝",
        )
    except Exception:
        notification_error = True
        logger.exception("Не удалось уведомить о выплате по заявке %s", request_id)

    suffix = "\n⚠️ Пользователя уведомить не удалось." if notification_error else ""
    await callback.message.edit_text(
        f"✅ Выплата по заявке #{request_id} выполнена.\nСумма: "
        f"{amount} {request['payment_method'].upper()}{suffix}",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer("✅ Выплата отмечена как выполненная")


@router.callback_query(F.data.startswith("payout_reject:"))
async def payout_rejected(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    request_id = _callback_id(callback.data)
    if not request_id:
        await callback.answer("❌ Некорректная заявка", show_alert=True)
        return
    await callback.message.edit_text(
        "❌ <b>Отказ в выплате</b>\n\nВыберите причину:",
        reply_markup=payout_reject_reason_kb(request_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payout_reject_reason:"))
async def payout_reject_reason(callback: CallbackQuery, bot: Bot):
    if not await _require_admin(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Некорректная команда", show_alert=True)
        return
    reason_key, request_id = parts[1], _callback_id(callback.data)
    request = await db.get_sale_request(request_id) if request_id else None
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    reasons = {
        "wrong_details": "Указаны некорректные реквизиты.",
        "not_transferred": "Канал не был передан.",
        "terms_violation": "Нарушены условия сделки.",
    }
    reason_text = reasons.get(reason_key)
    if not reason_text or not await db.reject_payout(request_id, reason_text):
        await callback.answer("❌ Выплата уже обработана", show_alert=True)
        return
    try:
        await bot.send_message(
            request["user_id"],
            f"❌ <b>В выплате отказано</b>\n\n<b>Причина:</b> {reason_text}\n"
            f"📋 Номер заявки: <code>{request_id}</code>",
        )
    except Exception:
        logger.exception("Не удалось уведомить об отказе выплаты %s", request_id)
    await callback.message.edit_text(
        f"❌ Выплата по заявке #{request_id} отклонена.\nПричина: {reason_text}",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer("Выплата отклонена")


@router.callback_query(F.data == "admin_payments")
async def show_payments(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    payments = await db.get_payments_all()
    text = "💳 <b>Все выплаты</b>\n\n"
    if not payments:
        await callback.message.edit_text(text + "Нет заявок на выплату.", reply_markup=back_to_admin_kb())
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"#{p['id']} - {p['status']} - {p['amount']} {p['currency'].upper()}",
                    callback_data=f"view_payment:{p['request_id']}",
                )
            ]
            for p in payments[:10]
        ]
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        await callback.message.edit_text(
            text + f"Всего заявок: {len(payments)}\n\n<i>Выберите заявку:</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("view_payment:"))
async def view_payment_details(callback: CallbackQuery):
    if not await _require_admin(callback):
        return
    request_id = _callback_id(callback.data)
    request = await db.get_sale_request(request_id) if request_id else None
    payment = await db.get_payment_by_request(request_id) if request_id else None
    if not request or not payment:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    text = f"""
💳 <b>Заявка на выплату #{request['id']}</b>

👤 <b>Пользователь:</b> @{safe_html(request['username'] or 'unknown')}
🆔 <b>ID:</b> <code>{request['user_id']}</code>
🔗 <b>Канал:</b> {safe_html(request['channel_link'] or 'N/A')}

💰 <b>Сумма:</b> {payment['amount']} {payment['currency'].upper()}

📝 <b>Реквизиты:</b>
<code>{safe_html(payment['payment_details'] or '')}</code>

📅 <b>Создана:</b> {payment['created_at']}
📍 <b>Статус:</b> <code>{safe_html(payment['status'])}</code>
"""
    if payment["paid_at"]:
        text += f"\n✅ <b>Выплачено:</b> {payment['paid_at']}"
    if payment["rejected_at"]:
        text += f"\n❌ <b>Отклонено:</b> {payment['rejected_at']}\nПричина: {safe_html(payment['rejection_reason'] or '')}"
    await callback.message.edit_text(text, reply_markup=payment_action_kb(request_id))
    await callback.answer()
