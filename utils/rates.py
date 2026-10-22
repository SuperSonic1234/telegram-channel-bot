import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RatesService:
    """Сервис для получения актуальных курсов валют"""
    
    # CoinGecko API для получения курса TON (GRAM)
    COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
    
    # Кэш курсов (обновляется каждые 5 минут)
    _cache = {}
    _cache_timeout = 300  # 5 минут
    
    @classmethod
    async def get_ton_to_rub_rate(cls) -> Optional[float]:
        """
        Получить актуальный курс TON/GRAM к рублю
        
        Returns:
            float: Курс TON к RUB или None при ошибке
        """
        try:
            params = {
                'ids': 'the-open-network',  # TON в CoinGecko
                'vs_currencies': 'rub'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(cls.COINGECKO_API, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = data.get('the-open-network', {}).get('rub')
                        
                        if rate:
                            logger.info(f"Получен курс TON: {rate} RUB")
                            return float(rate)
                        else:
                            logger.error("Не удалось получить курс TON из ответа API")
                            return None
                    else:
                        logger.error(f"Ошибка API CoinGecko: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при получении курса TON: {e}")
            return None
    
    @classmethod
    async def get_ton_to_usd_rate(cls) -> Optional[float]:
        """
        Получить актуальный курс TON к доллару
        
        Returns:
            float: Курс TON к USD или None при ошибке
        """
        try:
            params = {
                'ids': 'the-open-network',
                'vs_currencies': 'usd'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(cls.COINGECKO_API, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = data.get('the-open-network', {}).get('usd')
                        
                        if rate:
                            logger.info(f"Получен курс TON: {rate} USD")
                            return float(rate)
                        else:
                            logger.error("Не удалось получить курс TON из ответа API")
                            return None
                    else:
                        logger.error(f"Ошибка API CoinGecko: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при получении курса TON: {e}")
            return None


async def get_actual_rates():
    """
    Получить все актуальные курсы
    
    Returns:
        dict: Словарь с курсами или значения по умолчанию
    """
    ton_to_rub = await RatesService.get_ton_to_rub_rate()
    
    # Если не удалось получить курс, используем значение по умолчанию
    if ton_to_rub is None:
        logger.warning("Используется курс TON по умолчанию: 100 RUB")
        ton_to_rub = 100.0
    
    return {
        'gram_to_rub': ton_to_rub,
        'stars_to_gram': 0.01,  # 1 Star = 0.01 GRAM (константа)
        'telegram_withdrawal_fee': 7.0,  # 7% - комиссия Telegram
        'fragment_conversion_fee': 5.0,  # 5% - комиссия Fragment
    }
