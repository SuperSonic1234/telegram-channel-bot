import sqlite3

import pytest

from database import Database


@pytest.mark.asyncio
async def test_init_migrates_old_database(tmp_path):
    path = tmp_path / "nested" / "bot.db"
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            channels_sold INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE sale_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            total_balance REAL,
            available_balance REAL,
            hold_balance REAL,
            calculated_price_rub REAL,
            calculated_price_gram REAL,
            calculated_price_stars REAL,
            payment_method TEXT,
            payment_details TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    connection.close()

    db = Database(str(path))
    await db.init_db()

    connection = sqlite3.connect(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(sale_requests)")}
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    connection.close()
    assert "channel_link" in columns
    assert "payments" in tables


@pytest.mark.asyncio
async def test_sale_and_payout_are_idempotent(tmp_path):
    db = Database(str(tmp_path / "data" / "bot.db"))
    await db.init_db()
    await db.add_user(10, "seller")
    request_id = await db.create_sale_request(
        10,
        "seller",
        "@channel",
        1000,
        800,
        200,
        {"rub": 500, "gram": 5, "stars": 500},
    )
    await db.update_sale_request(request_id, payment_method="rub")
    assert await db.transition_sale_request(request_id, "pending", ("draft",))
    assert await db.transition_sale_request(request_id, "approved", ("pending",))
    await db.add_purchase(request_id, 10, "seller", "@channel", 500, "rub", "approved")
    assert await db.transition_sale_request(request_id, "awaiting_payout", ("approved",))
    await db.create_payment(request_id, 10, "card", 500, "rub")

    assert await db.complete_payout(request_id)
    assert not await db.complete_payout(request_id)

    user = await db.get_user(10)
    payment = await db.get_payment_by_request(request_id)
    request = await db.get_sale_request(request_id)
    history = await db.get_purchased_channels()
    assert user["channels_sold"] == 1
    assert user["total_earned"] == 500
    assert payment["status"] == "paid"
    assert request["status"] == "completed"
    assert history[0]["request_id"] == request_id


@pytest.mark.asyncio
async def test_reject_payout_updates_both_records(tmp_path):
    db = Database(str(tmp_path / "bot.db"))
    await db.init_db()
    await db.add_user(11, "seller")
    request_id = await db.create_sale_request(
        11, "seller", "@channel", 10, 10, 0, {"rub": 5, "gram": 1, "stars": 5}
    )
    await db.update_sale_request(request_id, payment_method="rub")
    await db.transition_sale_request(request_id, "awaiting_payout", ("draft",))
    await db.create_payment(request_id, 11, "card", 5, "rub")

    assert await db.reject_payout(request_id)
    assert not await db.reject_payout(request_id)
    assert (await db.get_sale_request(request_id))["status"] == "payout_rejected"
    assert (await db.get_payment_by_request(request_id))["status"] == "rejected"
