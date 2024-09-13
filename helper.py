import os
from datetime import datetime

from aiogram import types
from aiogram.types import InlineKeyboardButton, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import ClientSession
from requests import get

"""Создаем клавиатуру для подписок"""
kb_markup_subscribe = InlineKeyboardBuilder()
kb_markup_subscribe.row(
    InlineKeyboardButton(text='Статус подписки', callback_data='subscribe_status'),
    InlineKeyboardButton(text='Оплатить подписку', callback_data='subscribe_pay')
)
kb_markup_subscribe.row(
    InlineKeyboardButton(text='Проблемы с платежём', callback_data='subscribe_issues')
)

"""Создаем клавиатуру для обратной связи пользователя"""
kb_markup_support = InlineKeyboardBuilder()
kb_markup_support.add(
    InlineKeyboardButton(text='Консультация менеджера', callback_data='support_manager')
)

"""Создаем клавиатуру для главного меню"""
kb_menu = InlineKeyboardBuilder()
kb_menu.row(
    InlineKeyboardButton(text='Настроить склады', callback_data='warehouse_settings')
)
kb_menu.row(
    InlineKeyboardButton(text='Добавить токен', callback_data='token_yes')
)

"""Создаем клавиатуру для токена"""
kb_wrong_token = InlineKeyboardBuilder()
kb_wrong_token.row(
    InlineKeyboardButton(text='Инструкция по созданию токена', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
)
kb_wrong_token.row(
    InlineKeyboardButton(text='Продолжить без токена', callback_data='token_no')
)

kb_warehouse_setting_menu = InlineKeyboardBuilder()
kb_warehouse_setting_menu.row(
    InlineKeyboardButton(text='Изменить параметры складов', callback_data='warehouse_change'),
    InlineKeyboardButton(text='Добавить новый склад', callback_data='warehouse_add')
)
kb_warehouse_setting_menu.row(
    InlineKeyboardButton(text='В главное меню', callback_data='main_menu')
)

all_warehouses = get(os.environ.get('API_URL') + '/supplies/warehouses', params={'chat_id': os.environ.get('ADMIN_CHAT')}).json()
kb_all_warehouses = InlineKeyboardBuilder()
for warehouse in all_warehouses['data']:
    kb_all_warehouses.row(
        InlineKeyboardButton(
            text=f"{warehouse['warehouse_name']}",
            callback_data=f"{warehouse['warehouse_id']}__{warehouse['warehouse_name']}"
        )
    )

kb_confirm_adding_warehouse = InlineKeyboardBuilder()
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Да, все верно', callback_data='save')
)
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Коэффициент неверный', callback_data='change_coefficient')
)
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Интервал дат неверный', callback_data='change_dates')
)
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Отменить добавление склада', callback_data='cancel_adding')
)

# prices = get(os.environ.get('API_URL') + '/admin/tariffs', params={'chat_id': '526206350'}).json()
prices = {
    'success': True,
    'tariffs': [
        {
            'id': 1,
            'price': 100000,
            'description': 'Тариф базовый'
        },
    ]
}

PRICES = {}
PRICE_IDS = tuple(str(price['id']) for price in prices['tariffs'])
ADMINS_ID = [526206350, 53060580]

kb_markup_subscribe_tariff = InlineKeyboardBuilder()

for price in prices['tariffs']:
    PRICES[str(price['id'])] = LabeledPrice(label=price['description'], amount=price['price'])
    kb_markup_subscribe_tariff.row(
        InlineKeyboardButton(text=price['description'], callback_data=str(price['id']))
    )


def keyboard_work(function):
    async def decorator(call: types.CallbackQuery, state):
        await call.answer()
        answer = await function(call, state)
        await call.message.edit_reply_markup()
        return answer
    return decorator


async def make_request(url, params: dict, json_data=None, files=None, method='post') -> dict | bool:
    session = ClientSession(trust_env=True)
    url = os.environ.get('API_URL') + url
    if method == 'post':
        async with session.post(url=url, params=params, json=json_data, data=files) as response:
            print(response.status)
            if response.status < 500:
                answer = await response.json()
            else:
                answer = False
    else:
        async with session.get(url=url, params=params) as response:
            print(response.text)
            if response.status < 500:
                answer = await response.json()
            else:
                answer = False
    print(answer)
    await session.close()
    return answer
