import aiosqlite
from datetime import datetime
from config import DATABASE_PATH


class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    channels_sold INTEGER DEFAULT 0,
                    total_earned REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица заявок на продажу
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sale_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    channel_link TEXT,
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица истории покупок
            await db.execute("""
                CREATE TABLE IF NOT EXISTS purchase_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    channel_username TEXT,
                    purchase_date TIMESTAMP,
                    price REAL,
                    currency TEXT,
                    status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица обращений в поддержку
            await db.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица настроек бота
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Инициализация настроек по умолчанию
            await db.execute("""
                INSERT OR IGNORE INTO bot_settings (key, value) VALUES
                ('welcome_message', 'Добро пожаловать в бот скупки каналов! 👋'),
                ('commission_percent', '30'),
                ('support_contact', '@support'),
                ('stars_withdrawal_commission', '5'),
                ('gram_to_rub_rate', '100'),
                ('stars_to_gram_rate', '0.01')
            """)

            await db.commit()

    # === Методы для работы с пользователями ===
    async def add_user(self, user_id: int, username: str = None):
        """Добавить нового пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username)
                VALUES (?, ?)
            """, (user_id, username))
            await db.commit()

    async def get_user(self, user_id: int):
        """Получить данные пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                return await cursor.fetchone()

    async def update_user_stats(self, user_id: int, earned: float):
        """Обновить статистику пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users
                SET channels_sold = channels_sold + 1,
                    total_earned = total_earned + ?
                WHERE user_id = ?
            """, (earned, user_id))
            await db.commit()

    # === Методы для работы с заявками на продажу ===
    async def create_sale_request(self, user_id: int, username: str, channel_link: str,
                                   total_balance: float, available_balance: float,
                                   hold_balance: float, prices: dict):
        """Создать заявку на продажу"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO sale_requests
                (user_id, username, channel_link, total_balance, available_balance, hold_balance,
                 calculated_price_rub, calculated_price_gram, calculated_price_stars)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, channel_link, total_balance, available_balance, hold_balance,
                  prices['rub'], prices['gram'], prices['stars']))
            await db.commit()
            return cursor.lastrowid

    async def update_sale_request(self, request_id: int, **kwargs):
        """Обновить заявку на продажу"""
        async with aiosqlite.connect(self.db_path) as db:
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            query = f"UPDATE sale_requests SET {set_clause}, updated_at = ? WHERE id = ?"
            values = list(kwargs.values()) + [datetime.now().isoformat(), request_id]
            await db.execute(query, values)
            await db.commit()

    async def get_sale_request(self, request_id: int):
        """Получить заявку по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sale_requests WHERE id = ?
            """, (request_id,)) as cursor:
                return await cursor.fetchone()

    async def get_pending_requests(self):
        """Получить все ожидающие заявки"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sale_requests WHERE status = 'pending'
                ORDER BY created_at DESC
            """) as cursor:
                return await cursor.fetchall()

    async def get_user_requests(self, user_id: int):
        """Получить заявки пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sale_requests WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,)) as cursor:
                return await cursor.fetchall()

    # === Методы для работы с историей покупок ===
    async def add_purchase(self, user_id: int, username: str, channel_username: str,
                          price: float, currency: str, status: str):
        """Добавить запись о покупке"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO purchase_history
                (user_id, username, channel_username, purchase_date, price, currency, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, channel_username, datetime.now(), price, currency, status))
            await db.commit()

    async def get_purchased_channels(self):
        """Получить список купленных каналов"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM purchase_history WHERE status = 'bought'
                ORDER BY purchase_date DESC
            """) as cursor:
                return await cursor.fetchall()

    async def get_rejected_channels(self):
        """Получить список отказанных каналов"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM purchase_history WHERE status = 'rejected'
                ORDER BY purchase_date DESC
            """) as cursor:
                return await cursor.fetchall()

    # === Методы для работы с обращениями в поддержку ===
    async def create_ticket(self, user_id: int, username: str, message: str):
        """Создать обращение в поддержку"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO support_tickets (user_id, username, message)
                VALUES (?, ?, ?)
            """, (user_id, username, message))
            await db.commit()
            return cursor.lastrowid

    async def get_open_tickets(self):
        """Получить открытые обращения"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM support_tickets WHERE status = 'open'
                ORDER BY created_at DESC
            """) as cursor:
                return await cursor.fetchall()

    async def close_ticket(self, ticket_id: int):
        """Закрыть обращение"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE support_tickets
                SET status = 'closed', closed_at = ?
                WHERE id = ?
            """, (datetime.now(), ticket_id))
            await db.commit()

    # === Методы для работы с настройками ===
    async def get_setting(self, key: str):
        """Получить настройку"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT value FROM bot_settings WHERE key = ?
            """, (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_setting(self, key: str, value: str):
        """Установить настройку"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO bot_settings (key, value)
                VALUES (?, ?)
            """, (key, value))
            await db.commit()

    async def get_all_settings(self):
        """Получить все настройки"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM bot_settings") as cursor:
                return await cursor.fetchall()

    # === Статистика ===
    async def get_statistics(self):
        """Получить статистику бота"""
        async with aiosqlite.connect(self.db_path) as db:
            # Всего пользователей
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]

            # Всего заявок
            async with db.execute("SELECT COUNT(*) FROM sale_requests") as cursor:
                total_requests = (await cursor.fetchone())[0]

            # Одобренных заявок
            async with db.execute("""
                SELECT COUNT(*) FROM sale_requests WHERE status = 'approved'
            """) as cursor:
                approved_requests = (await cursor.fetchone())[0]

            # Всего заработано
            async with db.execute("SELECT SUM(total_earned) FROM users") as cursor:
                total_earned = (await cursor.fetchone())[0] or 0

            return {
                'total_users': total_users,
                'total_requests': total_requests,
                'approved_requests': approved_requests,
                'total_earned': total_earned
            }

    async def get_all_users(self):
        """Получить всех пользователей для рассылки"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cursor:
                return await cursor.fetchall()
