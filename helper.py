import os
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, LabeledPrice, ReplyKeyboardMarkup
from requests import get


kb_markup_start = ReplyKeyboardMarkup(resize_keyboard=True)
kb_markup_start.add(KeyboardButton('ОПиУ'), KeyboardButton('Юнит-экономика'))
kb_markup_start.add(KeyboardButton('Проверить подписку'))

kb_markup_download_opi = InlineKeyboardMarkup()
kb_markup_download_opi.add(InlineKeyboardButton('Детализация', callback_data='report_opi'), InlineKeyboardButton('Себестоимость', callback_data='costs_opi'))
kb_markup_download_opi.add(InlineKeyboardButton('Выкупы', callback_data='self_opi'), InlineKeyboardButton('Реклама', callback_data='ads_opi'))
kb_markup_download_opi.add(InlineKeyboardButton('Прочие расходы', callback_data='other_opi'))
kb_markup_download_opi.add(InlineKeyboardButton('Получить ОПиУ', callback_data='get_opi'))

kb_markup_download_unit = InlineKeyboardMarkup()
kb_markup_download_unit.add(InlineKeyboardButton('Детализация', callback_data='report_unit'), InlineKeyboardButton('Себестоимость', callback_data='costs_unit'))
kb_markup_download_unit.add(InlineKeyboardButton('Выкупы', callback_data='self_unit'), InlineKeyboardButton('Реклама', callback_data='ads_unit'))
kb_markup_download_unit.add(InlineKeyboardButton('Получить отчёт', callback_data='get_unit'))

kb_markup_subscribe = ReplyKeyboardMarkup(resize_keyboard=True)
kb_markup_subscribe.add(KeyboardButton('Статус подписки'), KeyboardButton('Оплатить подписку'))
kb_markup_subscribe.add(KeyboardButton('Проблемы с платежём'))
kb_markup_subscribe.add(KeyboardButton('Продолжить'))

kb_markup_get_first_time = InlineKeyboardMarkup()
kb_markup_get_first_time.add(InlineKeyboardButton('Сформировать!', callback_data='get_first_time'))

kb_markup_download_ads = InlineKeyboardMarkup()
kb_markup_download_ads.add(InlineKeyboardButton('Да', callback_data='ads_yes'))
kb_markup_download_ads.add(InlineKeyboardButton('Нет', callback_data='ads_no'))

kb_markup_download_other_expenses = InlineKeyboardMarkup()
kb_markup_download_other_expenses.add(InlineKeyboardButton('Да', callback_data='exp_yes'))
kb_markup_download_other_expenses.add(InlineKeyboardButton('Нет', callback_data='exp_no'))

kb_markup_download_selfs = InlineKeyboardMarkup()
kb_markup_download_selfs.add(InlineKeyboardButton('Да', callback_data='selfs_yes'))
kb_markup_download_selfs.add(InlineKeyboardButton('Нет', callback_data='selfs_no'))

kb_download_extra_report = InlineKeyboardMarkup()
kb_download_extra_report.add(InlineKeyboardButton('Второго файла нет, продолжить', callback_data='extra_repo_no'))

kb_lifetime_error = InlineKeyboardMarkup()
# kb_lifetime_error.add(InlineKeyboardButton('Тариф ПРО (отчеты за 6 месяцев)', callback_data='2'))
# kb_lifetime_error.add(InlineKeyboardButton('Тариф Премиум (неограченный период)', callback_data='3'))
kb_lifetime_error.add(InlineKeyboardButton('Загрузить новую детализацию', callback_data='extra_repo_yes'))

kb_brand_count_error = InlineKeyboardMarkup()
# kb_brand_count_error.add(InlineKeyboardButton('Тариф ПРО (3-5 брендов)', callback_data='2'))
# kb_brand_count_error.add(InlineKeyboardButton('Тариф Премиум (более 5 брендов)', callback_data='3'))
kb_brand_count_error.add(InlineKeyboardButton('Загрузить новую детализацию', callback_data='extra_repo_yes'))

kb_download_separately = InlineKeyboardMarkup()
kb_download_separately.add(InlineKeyboardButton('Для каждого бренда своя таблица', callback_data='separately_yes'))
kb_download_separately.add(InlineKeyboardButton('Все бренды в одной таблице', callback_data='separately_no'))

kb_change_cost_price = InlineKeyboardMarkup()
kb_change_cost_price.add(InlineKeyboardButton('Отредактировать себестоимость', callback_data='costs_yes'))
kb_change_cost_price.add(InlineKeyboardButton('Себестоимость не менялась', callback_data='costs_no'))

kb_markup_new_costs = InlineKeyboardMarkup()
kb_markup_new_costs.add(InlineKeyboardButton('Да', callback_data='new_costs_yes'))
kb_markup_new_costs.add(InlineKeyboardButton('Нет', callback_data='new_costs_no'))


kb_back = ReplyKeyboardMarkup(resize_keyboard=True)
kb_back.add(KeyboardButton('Отменить последнее действие'))

kb_markup_first = InlineKeyboardMarkup()
kb_markup_first.add(InlineKeyboardButton('Получить первый финансовый отчет', callback_data='first_time_report'))

kb_markup_support = InlineKeyboardMarkup()
kb_markup_support.add(InlineKeyboardButton('Загрузка детализации', callback_data='support_report'))
kb_markup_support.add(InlineKeyboardButton('Получение шаблонов расходов', callback_data='support_pattern'))
kb_markup_support.add(InlineKeyboardButton('Заполнение / загрузка расходов', callback_data='support_fill'))
kb_markup_support.add(InlineKeyboardButton('Получение отчетов', callback_data='support_pnl'))
kb_markup_support.add(InlineKeyboardButton('Оплата подписки', callback_data='support_sub'))
kb_markup_support.add(InlineKeyboardButton('Нарушение работы бота', callback_data='support_work'))
kb_markup_support.add(InlineKeyboardButton('Консультация менеджера', callback_data='support_manager'))

kb_markup_items_without_costs = InlineKeyboardMarkup()
kb_markup_items_without_costs.add(InlineKeyboardButton('Не считать эти товары в отчетах', callback_data='without_no'))
kb_markup_items_without_costs.add(InlineKeyboardButton('Считать с нулевой себестоимостью', callback_data='without_yes'))
kb_markup_items_without_costs.add(InlineKeyboardButton('Дополнить себестоимость', callback_data='without_rewrite'))

kb_markup_find_report = InlineKeyboardMarkup()
kb_markup_find_report.add(InlineKeyboardButton('Где найти детализацию?', url='https://telegra.ph/Gde-najti-detalizaciyu-07-25'))


# prices = get(os.environ.get('API_URL') + '/admin/tariffs', params={'chat_id': '526206350'}).json()
prices = {
    'success': True,
    'tariffs': [
        {
            'id': 1,
            'price': 149000,
            'description': 'Тариф базовый'
        }
        # {
        #     'id': 2,
        #     'price': 199000,
        #     'description': 'Тариф ПРО'
        # },
        # {
        #     'id': 3,
        #     'price': 999000,
        #     'description': 'Тариф Премиум'
        # }
    ]
}
PRICES = {}
PRICE_IDS = tuple(str(price['id']) for price in prices['tariffs'])
kb_markup_subscribe_tariff = InlineKeyboardMarkup()

for price in prices['tariffs']:
    PRICES[str(price['id'])] = LabeledPrice(label=price['description'], amount=price['price'])
    kb_markup_subscribe_tariff.add(InlineKeyboardButton(price['description'], callback_data=str(price['id'])))
