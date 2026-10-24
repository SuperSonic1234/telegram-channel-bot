from utils.rates import get_actual_rates


class ChannelPriceCalculator:
    """Калькулятор стоимости канала с учетом всех комиссий"""
    
    @staticmethod
    async def calculate_channel_price(
        total_stars: float,
        profit_percent: float = 30.0
    ) -> dict:
        """
        Рассчитать стоимость канала с учетом всех комиссий
        
        Args:
            total_stars: Общее количество звезд в канале
            profit_percent: Процент прибыли (по умолчанию 30%)
        
        Returns:
            dict: Детальный расчет с ценами в разных валютах
        """
        if total_stars <= 0:
            raise ValueError("Количество Stars должно быть больше нуля")
        if not 0 <= profit_percent <= 100:
            raise ValueError("Процент прибыли должен быть от 0 до 100")

        # Получаем актуальные курсы
        rates = await get_actual_rates()
        
        gram_to_rub = rates['gram_to_rub']
        stars_to_rub = rates['stars_to_rub']
        telegram_fee = rates['telegram_withdrawal_fee']
        fragment_fee = rates['fragment_conversion_fee']
        
        # Шаг 1: Вывод с канала Telegram (минус комиссия Telegram)
        stars_after_telegram = total_stars * (1 - telegram_fee / 100)
        
        # Шаг 2: Конвертация Stars → GRAM через Fragment (минус комиссия Fragment)
        stars_after_fragment = stars_after_telegram * (1 - fragment_fee / 100)
        rub_amount = stars_after_fragment * stars_to_rub
        gram_amount = rub_amount / gram_to_rub
        
        # Шаг 3: Конвертация GRAM → RUB
        # Шаг 4: Вычитаем процент прибыли
        final_price_rub = rub_amount * (1 - profit_percent / 100)
        
        # Рассчитываем цены в других валютах
        final_price_gram = final_price_rub / gram_to_rub
        final_price_stars = final_price_rub / stars_to_rub
        
        return {
            # Исходные данные
            'initial_stars': total_stars,
            'profit_percent': profit_percent,
            
            # Комиссии
            'telegram_fee_percent': telegram_fee,
            'fragment_fee_percent': fragment_fee,
            
            # Промежуточные расчеты
            'stars_after_telegram': stars_after_telegram,
            'stars_after_fragment': stars_after_fragment,
            'gram_after_conversion': gram_amount,
            'rub_after_conversion': rub_amount,
            
            # Итоговые цены (после вычета прибыли)
            'final_price_rub': round(final_price_rub, 2),
            'final_price_gram': round(final_price_gram, 4),
            'final_price_stars': round(final_price_stars, 2),
            
            # Курсы
            'gram_to_rub_rate': gram_to_rub,
            'stars_to_rub_rate': stars_to_rub,
            'stars_to_gram_rate': stars_to_rub / gram_to_rub,
        }
    
    @staticmethod
    async def calculate_net_amount(total_stars: float) -> dict:
        """
        Рассчитать чистую сумму после вывода (без вычета прибыли)
        Используется в калькуляторе админки
        
        Args:
            total_stars: Количество звезд
        
        Returns:
            dict: Чистые суммы в разных валютах
        """
        if total_stars <= 0:
            raise ValueError("Количество Stars должно быть больше нуля")
        rates = await get_actual_rates()
        
        gram_to_rub = rates['gram_to_rub']
        stars_to_rub = rates['stars_to_rub']
        telegram_fee = rates['telegram_withdrawal_fee']
        fragment_fee = rates['fragment_conversion_fee']
        
        # Вывод с канала
        stars_after_telegram = total_stars * (1 - telegram_fee / 100)
        
        # Конвертация через Fragment
        stars_after_fragment = stars_after_telegram * (1 - fragment_fee / 100)
        rub_amount = stars_after_fragment * stars_to_rub
        gram_amount = rub_amount / gram_to_rub
        
        # Конвертация в рубли
        return {
            'initial_stars': total_stars,
            'telegram_fee_percent': telegram_fee,
            'fragment_fee_percent': fragment_fee,
            'stars_after_telegram': round(stars_after_telegram, 2),
            'stars_after_fragment': round(stars_after_fragment, 2),
            'net_gram': round(gram_amount, 4),
            'net_rub': round(rub_amount, 2),
            'gram_to_rub_rate': gram_to_rub,
            'stars_to_rub_rate': stars_to_rub,
            'stars_to_gram_rate': stars_to_rub / gram_to_rub,
        }
    
    @staticmethod
    def format_price_message(calculation: dict) -> str:
        """
        Форматировать сообщение с расчетом цены

        Args:
            calculation: Результат расчета из calculate_channel_price

        Returns:
            str: Отформатированное сообщение
        """
        return f"""
💰 <b>Расчет стоимости канала</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 МЫ ГОТОВЫ КУПИТЬ ВАШ КАНАЛ ЗА:</b>

💵 <code>{calculation['final_price_rub']:,.2f}</code> RUB
💎 <code>{calculation['final_price_gram']:.4f}</code> GRAM
⭐ <code>{calculation['final_price_stars']:,.0f}</code> Stars

━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>✅ Расчет выполнен с учетом всех комиссий и текущих курсов</i>
"""
    
    @staticmethod
    def format_calculator_message(calculation: dict) -> str:
        """
        Форматировать сообщение калькулятора (без вычета прибыли)
        
        Args:
            calculation: Результат расчета из calculate_net_amount
        
        Returns:
            str: Отформатированное сообщение
        """
        return f"""
🧮 <b>Калькулятор выплат</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💫 <b>Исходная сумма:</b> <code>{calculation['initial_stars']:,.0f}</code> Stars

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Этап 1: Вывод с канала Telegram</b>
├─ Комиссия: <code>-{calculation['telegram_fee_percent']}%</code>
└─ Остаток: <code>{calculation['stars_after_telegram']:,.2f}</code> Stars

💎 <b>Этап 2: Конвертация через Fragment</b>
├─ Комиссия: <code>-{calculation['fragment_fee_percent']}%</code>
└─ К конвертации: <code>{calculation['stars_after_fragment']:,.2f}</code> Stars

━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💰 ЧИСТАЯ СУММА (после всех комиссий):</b>

💎 <code>{calculation['net_gram']:.4f}</code> GRAM
💵 <code>{calculation['net_rub']:,.2f}</code> RUB

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>Текущие курсы:</b>
├─ 1 Star = <code>{calculation['stars_to_rub_rate']:.6f}</code> RUB
└─ 1 GRAM = <code>{calculation['gram_to_rub_rate']:.2f}</code> RUB

<i>💡 Курс TON обновляется автоматически</i>
"""
