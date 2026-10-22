import asyncio
import logging
import time

import aiohttp

from database import Database

logger = logging.getLogger(__name__)


class RatesService:
    """Fetch and cache the TON/RUB rate."""

    COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
    _cached_ton_to_rub: float | None = None
    _cache_time = 0.0
    _cache_timeout = 300.0
    _lock = asyncio.Lock()

    @classmethod
    async def get_ton_to_rub_rate(cls) -> float | None:
        now = time.monotonic()
        if cls._cached_ton_to_rub is not None and now - cls._cache_time < cls._cache_timeout:
            return cls._cached_ton_to_rub

        async with cls._lock:
            now = time.monotonic()
            if cls._cached_ton_to_rub is not None and now - cls._cache_time < cls._cache_timeout:
                return cls._cached_ton_to_rub
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                params = {"ids": "the-open-network", "vs_currencies": "rub"}
                async with (
                    aiohttp.ClientSession(timeout=timeout) as session,
                    session.get(cls.COINGECKO_API, params=params) as response,
                ):
                    response.raise_for_status()
                    data = await response.json()
                rate = float(data["the-open-network"]["rub"])
                if rate <= 0:
                    raise ValueError("TON rate must be positive")
                cls._cached_ton_to_rub = rate
                cls._cache_time = now
                return rate
            except (TimeoutError, aiohttp.ClientError, KeyError, TypeError, ValueError) as exc:
                logger.warning("Не удалось получить курс TON/RUB: %s", exc)
                return None


async def _positive_setting(db: Database, key: str, default: float) -> float:
    try:
        value = float(await db.get_setting(key) or default)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


async def _percent_setting(db: Database, key: str, default: float) -> float:
    try:
        value = float(await db.get_setting(key) or default)
        return value if 0 <= value <= 100 else default
    except (TypeError, ValueError):
        return default


async def get_actual_rates() -> dict[str, float]:
    """Return rates with admin settings applied and safe fallbacks."""
    db = Database()
    fallback_ton = await _positive_setting(db, "gram_to_rub_rate", 100.0)
    override_raw = await db.get_setting("gram_to_rub_override")
    try:
        override = float(override_raw) if override_raw else None
        if override is not None and override <= 0:
            override = None
    except (TypeError, ValueError):
        override = None

    ton_to_rub = override or await RatesService.get_ton_to_rub_rate() or fallback_ton
    stars_to_gram = await _positive_setting(db, "stars_to_gram_rate", 0.01)
    withdrawal_fee = await _percent_setting(db, "stars_withdrawal_commission", 5.0)

    return {
        "gram_to_rub": ton_to_rub,
        "stars_to_gram": stars_to_gram,
        "telegram_withdrawal_fee": withdrawal_fee,
        "fragment_conversion_fee": 5.0,
    }
