from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import aiosqlite

from config import DATABASE_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017 - server runs Python 3.10


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = str(db_path)

    def _ensure_parent_dir(self) -> None:
        path = Path(self.db_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)

    async def _connect(self) -> aiosqlite.Connection:
        self._ensure_parent_dir()
        db = await aiosqlite.connect(self.db_path)
        await db.execute("PRAGMA foreign_keys = ON")
        return db

    async def init_db(self) -> None:
        """Create the schema and apply idempotent migrations."""
        db = await self._connect()
        try:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    channels_sold INTEGER NOT NULL DEFAULT 0,
                    total_earned REAL NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sale_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    channel_link TEXT,
                    total_balance REAL NOT NULL,
                    available_balance REAL NOT NULL,
                    hold_balance REAL NOT NULL,
                    calculated_price_rub REAL NOT NULL,
                    calculated_price_gram REAL NOT NULL,
                    calculated_price_stars REAL NOT NULL,
                    payment_method TEXT,
                    payment_details TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );

                CREATE TABLE IF NOT EXISTS purchase_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    channel_username TEXT,
                    purchase_date TIMESTAMP,
                    price REAL,
                    currency TEXT,
                    status TEXT,
                    FOREIGN KEY (request_id) REFERENCES sale_requests (id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );

                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    message TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    payment_details TEXT,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES sale_requests (id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );

                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS request_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES sale_requests (id)
                );
                """
            )

            await self._add_column_if_missing(db, "sale_requests", "channel_link", "TEXT")
            await self._add_column_if_missing(db, "sale_requests", "calculation_details", "TEXT")
            await self._add_column_if_missing(db, "sale_requests", "rejection_reason", "TEXT")
            await self._add_column_if_missing(db, "purchase_history", "request_id", "INTEGER")
            await self._add_column_if_missing(db, "payments", "rejected_at", "TIMESTAMP")
            await self._add_column_if_missing(db, "payments", "rejection_reason", "TEXT")

            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_request_id ON payments(request_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_sale_requests_status ON sale_requests(status)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_request_events_request_id ON request_events(request_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)"
            )

            await db.executemany(
                "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
                [
                    ("welcome_message", "Добро пожаловать в бот скупки каналов! 👋"),
                    ("commission_percent", "30"),
                    ("minimum_sale_balance", "0"),
                    ("support_contact", "@support"),
                    ("stars_withdrawal_commission", "5"),
                    ("fragment_conversion_commission", "5"),
                    ("gram_to_rub_rate", "100"),
                    ("gram_to_rub_override", ""),
                    ("stars_to_gram_rate", "0.01"),
                    ("stars_to_rub_rate", "1"),
                ],
            )
            await db.commit()
        finally:
            await db.close()

    @staticmethod
    async def _add_column_if_missing(
        db: aiosqlite.Connection, table: str, column: str, definition: str
    ) -> None:
        async with db.execute(f"PRAGMA table_info({table})") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if column not in columns:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    async def add_user(self, user_id: int, username: str | None = None) -> None:
        db = await self._connect()
        try:
            await db.execute(
                """
                INSERT INTO users (user_id, username) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
                """,
                (user_id, username),
            )
            await db.commit()
        finally:
            await db.close()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        db = await self._connect()
        try:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                return await cursor.fetchone()
        finally:
            await db.close()

    async def create_sale_request(
        self,
        user_id: int,
        username: str,
        channel_link: str,
        total_balance: float,
        available_balance: float,
        hold_balance: float,
        prices: dict[str, float],
        calculation: dict[str, Any] | None = None,
    ) -> int:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                INSERT INTO sale_requests
                (user_id, username, channel_link, total_balance, available_balance, hold_balance,
                 calculated_price_rub, calculated_price_gram, calculated_price_stars,
                 calculation_details, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
                """,
                (
                    user_id,
                    username,
                    channel_link,
                    total_balance,
                    available_balance,
                    hold_balance,
                    prices["rub"],
                    prices["gram"],
                    prices["stars"],
                    json.dumps(calculation or {}, ensure_ascii=False, default=str),
                ),
            )
            await db.commit()
            request_id = int(cursor.lastrowid)
            await self._add_event(db, request_id, "created", None, "draft", calculation or {})
            await db.commit()
            return request_id
        finally:
            await db.close()

    async def update_sale_request(self, request_id: int, **kwargs: Any) -> bool:
        if not kwargs:
            return False
        allowed = {"payment_method", "payment_details", "status", "channel_link", "rejection_reason"}
        unknown = set(kwargs) - allowed
        if unknown:
            raise ValueError(f"Unsupported sale request fields: {', '.join(sorted(unknown))}")

        set_clause = ", ".join(f"{key} = ?" for key in kwargs)
        values = [*kwargs.values(), utc_now(), request_id]
        db = await self._connect()
        try:
            cursor = await db.execute(
                f"UPDATE sale_requests SET {set_clause}, updated_at = ? WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount == 1
        finally:
            await db.close()

    async def transition_sale_request(
        self, request_id: int, new_status: str, allowed_statuses: Iterable[str]
    ) -> bool:
        statuses = tuple(allowed_statuses)
        if not statuses:
            return False
        placeholders = ", ".join("?" for _ in statuses)
        db = await self._connect()
        try:
            async with db.execute("SELECT status FROM sale_requests WHERE id = ?", (request_id,)) as status_cursor:
                current = await status_cursor.fetchone()
            cursor = await db.execute(
                f"""
                UPDATE sale_requests SET status = ?, updated_at = ?
                WHERE id = ? AND status IN ({placeholders})
                """,
                (new_status, utc_now(), request_id, *statuses),
            )
            await db.commit()
            if cursor.rowcount == 1:
                await self._add_event(db, request_id, "status_changed", current[0] if current else None, new_status)
                await db.commit()
            return cursor.rowcount == 1
        finally:
            await db.close()

    async def get_sale_request(self, request_id: int) -> aiosqlite.Row | None:
        db = await self._connect()
        try:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sale_requests WHERE id = ?", (request_id,)) as cursor:
                return await cursor.fetchone()
        finally:
            await db.close()

    async def get_pending_requests(self) -> list[aiosqlite.Row]:
        return await self._fetchall(
            "SELECT * FROM sale_requests WHERE status = 'pending' ORDER BY created_at DESC"
        )

    async def get_user_requests(self, user_id: int) -> list[aiosqlite.Row]:
        return await self._fetchall(
            "SELECT * FROM sale_requests WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        )

    async def get_all_sale_requests(self) -> list[aiosqlite.Row]:
        return await self._fetchall("SELECT * FROM sale_requests ORDER BY created_at DESC")

    async def get_request_events(self, request_id: int) -> list[aiosqlite.Row]:
        return await self._fetchall(
            "SELECT * FROM request_events WHERE request_id = ? ORDER BY created_at ASC, id ASC",
            (request_id,),
        )

    async def get_request_bundle(self, request_id: int) -> dict[str, Any] | None:
        request = await self.get_sale_request(request_id)
        if not request:
            return None
        return {
            "request": request,
            "payment": await self.get_payment_by_request(request_id),
            "events": await self.get_request_events(request_id),
        }

    async def _add_event(
        self, db: aiosqlite.Connection, request_id: int, event_type: str,
        old_status: str | None = None, new_status: str | None = None,
        details: Any = None,
    ) -> None:
        await db.execute(
            "INSERT INTO request_events (request_id, event_type, old_status, new_status, details) VALUES (?, ?, ?, ?, ?)",
            (request_id, event_type, old_status, new_status, json.dumps(details or {}, ensure_ascii=False, default=str)),
        )

    async def add_purchase(
        self,
        request_id: int,
        user_id: int,
        username: str,
        channel_username: str,
        price: float,
        currency: str,
        status: str,
    ) -> None:
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT id FROM purchase_history WHERE request_id = ?", (request_id,)
            ) as cursor:
                existing = await cursor.fetchone()
            if existing:
                await db.execute(
                    """
                    UPDATE purchase_history
                    SET channel_username = ?, price = ?, currency = ?, status = ?
                    WHERE request_id = ?
                    """,
                    (channel_username, price, currency, status, request_id),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO purchase_history
                    (request_id, user_id, username, channel_username, purchase_date, price, currency, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (request_id, user_id, username, channel_username, utc_now(), price, currency, status),
                )
            await db.commit()
        finally:
            await db.close()

    async def get_purchased_channels(self) -> list[aiosqlite.Row]:
        return await self._fetchall(
            "SELECT * FROM purchase_history WHERE status = 'bought' ORDER BY purchase_date DESC"
        )

    async def get_rejected_channels(self) -> list[aiosqlite.Row]:
        return await self._fetchall(
            "SELECT * FROM purchase_history WHERE status = 'rejected' ORDER BY purchase_date DESC"
        )

    async def create_ticket(self, user_id: int, username: str, message: str) -> int:
        db = await self._connect()
        try:
            cursor = await db.execute(
                "INSERT INTO support_tickets (user_id, username, message) VALUES (?, ?, ?)",
                (user_id, username, message),
            )
            await db.commit()
            return int(cursor.lastrowid)
        finally:
            await db.close()

    async def get_open_tickets(self) -> list[aiosqlite.Row]:
        return await self._fetchall(
            "SELECT * FROM support_tickets WHERE status = 'open' ORDER BY created_at DESC"
        )

    async def get_ticket(self, ticket_id: int) -> aiosqlite.Row | None:
        db = await self._connect()
        try:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)
            ) as cursor:
                return await cursor.fetchone()
        finally:
            await db.close()

    async def close_ticket(self, ticket_id: int) -> bool:
        db = await self._connect()
        try:
            cursor = await db.execute(
                """
                UPDATE support_tickets SET status = 'closed', closed_at = ?
                WHERE id = ? AND status = 'open'
                """,
                (utc_now(), ticket_id),
            )
            await db.commit()
            return cursor.rowcount == 1
        finally:
            await db.close()

    async def get_setting(self, key: str) -> str | None:
        db = await self._connect()
        try:
            async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        finally:
            await db.close()

    async def set_setting(self, key: str, value: str) -> None:
        db = await self._connect()
        try:
            await db.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value)
            )
            await db.commit()
        finally:
            await db.close()

    async def get_all_settings(self) -> list[aiosqlite.Row]:
        return await self._fetchall("SELECT * FROM bot_settings")

    async def get_statistics(self) -> dict[str, float | int]:
        db = await self._connect()
        try:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM sale_requests WHERE status != 'draft'") as cursor:
                total_requests = (await cursor.fetchone())[0]
            async with db.execute(
                "SELECT COUNT(*) FROM sale_requests WHERE status IN ('approved', 'awaiting_payout', 'completed')"
            ) as cursor:
                approved_requests = (await cursor.fetchone())[0]
            async with db.execute("SELECT SUM(total_earned) FROM users") as cursor:
                total_earned = (await cursor.fetchone())[0] or 0
            return {
                "total_users": total_users,
                "total_requests": total_requests,
                "approved_requests": approved_requests,
                "total_earned": total_earned,
            }
        finally:
            await db.close()

    async def get_all_users(self) -> list[aiosqlite.Row]:
        return await self._fetchall("SELECT * FROM users")

    async def get_payments_pending(self) -> list[aiosqlite.Row]:
        return await self._fetchall(
            """
            SELECT p.id, p.request_id, p.user_id, p.payment_details, p.amount, p.currency,
                   r.username, r.channel_link, p.created_at
            FROM payments p
            JOIN sale_requests r ON p.request_id = r.id
            WHERE p.status = 'pending'
            ORDER BY p.created_at DESC
            """
        )

    async def get_payments_all(self) -> list[aiosqlite.Row]:
        return await self._fetchall(
            """
            SELECT p.id, p.request_id, p.user_id, p.payment_details, p.amount, p.currency,
                   p.status, p.created_at, p.paid_at, p.rejected_at, p.rejection_reason,
                   r.username, r.channel_link
            FROM payments p
            JOIN sale_requests r ON p.request_id = r.id
            ORDER BY p.created_at DESC
            """
        )

    async def get_payment_by_request(self, request_id: int) -> aiosqlite.Row | None:
        db = await self._connect()
        try:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE request_id = ?", (request_id,)
            ) as cursor:
                return await cursor.fetchone()
        finally:
            await db.close()

    async def create_payment(
        self,
        request_id: int,
        user_id: int,
        payment_details: str,
        amount: float,
        currency: str,
    ) -> int:
        db = await self._connect()
        try:
            await db.execute(
                """
                INSERT INTO payments
                    (request_id, user_id, payment_details, amount, currency, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                ON CONFLICT(request_id) DO UPDATE SET
                    payment_details = excluded.payment_details,
                    amount = excluded.amount,
                    currency = excluded.currency,
                    status = 'pending',
                    paid_at = NULL
                """,
                (request_id, user_id, payment_details, amount, currency),
            )
            async with db.execute(
                "SELECT id FROM payments WHERE request_id = ?", (request_id,)
            ) as cursor:
                payment_id = (await cursor.fetchone())[0]
            await db.commit()
            await self._add_event(
                db, request_id, "payment_details_submitted", "approved", "awaiting_payout",
                {"amount": amount, "currency": currency, "payment_details": payment_details},
            )
            await db.commit()
            return int(payment_id)
        finally:
            await db.close()

    async def complete_payout(self, request_id: int) -> bool:
        """Finish one payout and update stats/history exactly once."""
        db = await self._connect()
        try:
            await db.execute("BEGIN IMMEDIATE")
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sale_requests WHERE id = ?", (request_id,)
            ) as cursor:
                request = await cursor.fetchone()
            async with db.execute(
                "SELECT * FROM payments WHERE request_id = ?", (request_id,)
            ) as cursor:
                payment = await cursor.fetchone()

            if (
                not request
                or not payment
                or request["status"] != "awaiting_payout"
                or payment["status"] != "pending"
            ):
                await db.rollback()
                return False

            now = utc_now()
            await db.execute(
                "UPDATE payments SET status = 'paid', paid_at = ? WHERE request_id = ?",
                (now, request_id),
            )
            await db.execute(
                "UPDATE sale_requests SET status = 'completed', updated_at = ? WHERE id = ?",
                (now, request_id),
            )
            await db.execute(
                """
                UPDATE users SET channels_sold = channels_sold + 1,
                                 total_earned = total_earned + ?
                WHERE user_id = ?
                """,
                (request["calculated_price_rub"], request["user_id"]),
            )
            await db.execute(
                "UPDATE purchase_history SET status = 'bought' WHERE request_id = ?",
                (request_id,),
            )
            await self._add_event(
                db, request_id, "payout_completed", "awaiting_payout", "completed",
                {"payment_id": payment["id"], "amount": payment["amount"], "currency": payment["currency"]},
            )
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()

    async def reject_payout(self, request_id: int, reason: str | None = None) -> bool:
        db = await self._connect()
        try:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                """
                UPDATE payments
                SET status = 'rejected', rejected_at = ?, rejection_reason = ?
                WHERE request_id = ? AND status = 'pending'
                """,
                (utc_now(), reason, request_id),
            )
            if cursor.rowcount != 1:
                await db.rollback()
                return False
            request_cursor = await db.execute(
                """
                UPDATE sale_requests SET status = 'payout_rejected', updated_at = ?
                WHERE id = ? AND status = 'awaiting_payout'
                """,
                (utc_now(), request_id),
            )
            if request_cursor.rowcount != 1:
                await db.rollback()
                return False
            await self._add_event(
                db, request_id, "payout_rejected", "awaiting_payout", "payout_rejected",
                {"reason": reason or ""},
            )
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()

    async def _fetchall(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> list[aiosqlite.Row]:
        db = await self._connect()
        try:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()
        finally:
            await db.close()
