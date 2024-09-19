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

all_warehouses_buttons = []
all_warehouses_names = {}
for warehouse in all_warehouses['data']:
    all_warehouses_names[warehouse['warehouse_id']] = warehouse['warehouse_name']
    all_warehouses_buttons.append(InlineKeyboardButton(
        text=warehouse['warehouse_name'],
        callback_data=warehouse['warehouse_id']
    ))

kb_confirm_adding_warehouse = InlineKeyboardBuilder()
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Да, все верно', callback_data='save')
)
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Коэффициент неверный', callback_data='change_coefficient_adding')
)
kb_confirm_adding_warehouse.row(
    InlineKeyboardButton(text='Интервал дат неверный', callback_data='change_dates_adding')
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


def create_update_keyboard(warehouse_id, warehouse_info) -> InlineKeyboardBuilder:
    kb_to_update = InlineKeyboardBuilder()
    kb_to_update.row(
        InlineKeyboardButton(
            text="Выключить отслеживание"
            if warehouse_info['is_active'] else "Включить отслеживание",
            callback_data=f'change_is_active__{warehouse_id}'
        ),
        InlineKeyboardButton(
            text='Изменить коэффициент',
            callback_data=f'change_coefficient__{warehouse_id}'
        ),
        InlineKeyboardButton(
            text='Изменить интервал',
            callback_data=f'change_interval__{warehouse_id}'
        )
    )
    kb_to_update.row(
        InlineKeyboardButton(
            text='Сохранить и выйти',
            callback_data='change_save'
        ),
        InlineKeyboardButton(
            text='Отменить и выйти',
            callback_data='change_cancel'
        )
    )
    return kb_to_update


def fill_kb_all_warehouses(sheet: int) -> InlineKeyboardBuilder:
    kb_all_warehouses = InlineKeyboardBuilder()
    for i in range(sheet * 9, (sheet + 1) * 9):
        kb_all_warehouses.row(all_warehouses_buttons[i])
    kb_all_warehouses.adjust(3)
    kb_all_warehouses.row(
        InlineKeyboardButton(text='< сюда', callback_data='warehouse_list__previous'),
        InlineKeyboardButton(text='> туда', callback_data='warehouse_list__next')
    )
    return kb_all_warehouses
