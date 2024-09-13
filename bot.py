import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aioredis.client import Redis

import subscribe_payment
import support
from helper import kb_markup_subscribe, make_request, keyboard_work, kb_menu, kb_wrong_token, kb_all_warehouses, \
    kb_confirm_adding_warehouse, kb_warehouse_setting_menu
from states import AddToken, AddWarehouse

redis_connection = Redis(host=os.environ.get('REDIS_URL'), port=6379, db=0, password=os.environ.get('REDIS_PASSWORD'))
state_storage = RedisStorage(redis_connection)
update_ids = set()


bot = Bot(token=os.environ.get('API_TOKEN'))
dp = Dispatcher(storage=state_storage)
dp.include_routers(subscribe_payment.router, support.router)


@dp.message(Command('start'))
async def send_welcome(message: types.Message, state):
    await state.finish()
    answer = await make_request(
        url='/start',
        params={'chat_id': message.chat.id},
        json_data={
            'chat_id': message.chat.id,
            'username': message.chat.username,
        }
    )
    if not answer['success']:
        answer = await make_request(
            url='/users',
            params={'chat_id': message.chat.id},
            method='get'
        )
        if not answer['success']:
            await message.answer('Ваша подписка просрочена, оплатите', reply_markup=kb_markup_subscribe)
            return
    else:
        await message.answer(
            'Я могу уведомлять тебя о наличии бесплатной приемки товара на WB.'
            'Если хочешь точно отслеживать коэффициенты, отправь мне WB API токен для поставок',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_menu.as_markup()
        )
        return


@dp.callback_query(F.data == 'token_yes')
@keyboard_work
async def add_token_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        'Отправь мне свой токен из личного кабинета WB для поставок с флагом только на чтение',
        reply_markup=kb_wrong_token.as_markup(),
    )
    await state.set_state(AddToken.wait)


@dp.callback_query(F.data == 'token_no')
@dp.callback_query(F.data == 'main_menu')
@dp.callback_query(F.data == 'cancel_adding')
@keyboard_work
async def finish_token_adding(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.data == 'token_no':
        return await callback.message.answer(
            'Отлично, давай настроим склады',
            reply_markup=kb_warehouse_setting_menu.as_markup()
        )
    await callback.message.answer(
        'Что хочешь сделать?',
        reply_markup=kb_menu.as_markup()
    )


@dp.message(AddToken.wait)
async def add_token(message: types.Message, state: FSMContext):
    answer = await make_request(
        url='/supplies/token',
        params={'chat_id': message.chat.id},
        json_data={
            'value': message.text,
        }
    )
    if answer['success']:
        await state.clear()
        return await message.answer('Токен успешно добавлен!', reply_markup=kb_warehouse_setting_menu.as_markup())

    await message.answer(
        'Ты ввел неверный токен, отправь заново, следуй инструкции для создания токена '
        'или продолжи получать уведомления без токена',
        parse_mode=kb_wrong_token.as_markup()
    )


@dp.callback_query(F.data == 'warehouse_change')
@dp.callback_query(F.data == 'warehouse_add')
@keyboard_work
async def setup_warehouses(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'warehouse_change':
        warehouses = await make_request(
            url='/supplies/warehouses',
            params={'chat_id': callback.message.chat.id},
            method='get'
        )
        kb_warehouses = InlineKeyboardBuilder()
        for warehouse in warehouses['data']:
            kb_warehouses.row(
                InlineKeyboardButton(
                    text=f"{warehouse['warehouse_name']} "
                         f"коэффициент: {warehouse['coefficient']} "
                         f"с {warehouse['start_date']} до {warehouses['finish_date']}",
                    callback_data=f"warehouse_update__{warehouse['id']}"
                )
            )
        return await callback.message.answer(
            'Итак, выбери какой склад желаешь изменить',
            reply_markup=kb_warehouses.as_markup()
        )
    elif callback.data == 'warehouse_add':
        await state.set_state(AddWarehouse.name)
        return await callback.message.answer('Выберите из списка склад', reply_markup=kb_all_warehouses.as_markup())


@dp.callback_query(AddWarehouse.name)
@keyboard_work
async def fill_warehouse_name(callback: types.CallbackQuery, state: FSMContext):
    warehouse_id, warehouse_name = callback.data.split('__')
    await state.set_data({'warehouse_name': warehouse_name, 'warehouse_id': warehouse_id})
    await state.set_state(AddWarehouse.coefficient)
    return await callback.message.answer('Отправь коэффициент, ниже которого тебя необходимо уведомлять, например 5')


@dp.message(AddWarehouse.coefficient)
async def fill_coefficient(message: types.Message, state: FSMContext):
    data = await state.get_data()
    coefficient = message.text
    data['coefficient'] = coefficient
    await state.set_data(data)
    await state.set_state(AddWarehouse.interval)
    return await message.answer(
        'Осталось совсем чуть-чуть, отправь интервал дат, в которые ты хочешь, чтобы я следил за поставками.\n\n '
        'Например 01.01.2024 - 15.01.2024'
    )


@dp.message(AddWarehouse.interval)
async def fill_start_and_finish_date_and_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    start_date, finish_date = message.text.split(' - ')
    data.update(start_date=start_date, finish_date=finish_date)
    await state.set_data(data)
    await state.set_state(AddWarehouse.confirm)
    return await message.answer(
        f"Ты хочешь добавить склад {data['warehouse_name']} "
        f"с коэффициентом {data['coefficient']} "
        f"на даты с {data['start_date']} по {data['finish_date']}?",
        reply_markup=kb_confirm_adding_warehouse.as_markup()
    )


@dp.callback_query(F.data == 'save')
@keyboard_work
async def save_warehouse(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    answer = await make_request(
        url='supplies/warehouses',
        params={'chat_id': callback.message.chat.id},
        json_data=data,
    )
    print(answer)
    return await callback.message.answer('Отлично, склад добавлен в отслеживание', reply_markup=kb_menu.as_markup())


@dp.callback_query(F.data == 'change_coefficient')
@keyboard_work
async def change_coefficient(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddWarehouse.coefficient)
    return await callback.message.answer('Отправь коэффициент, ниже которого тебя необходимо уведомлять, например 5')


@dp.callback_query(F.data == 'change_dates')
@keyboard_work
async def change_interval(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddWarehouse.interval)
    return await callback.message.answer(
        'Осталось совсем чуть-чуть, отправь интервал дат, в которые ты хочешь, чтобы я следил за поставками.\n\n '
        'Например 01.01.2024 - 15.01.2024'
    )


@dp.callback_query(F.data.split("__")[0] == "warehouse_update")
@keyboard_work
async def select_update_fields(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    warehouse_id = callback.data.split('__')[1]
    warehouse_information = await make_request(
        url=f"/supplies/warehouses/{warehouse_id}",
        params={'chat_id': callback.message.chat.id},
        method='get'
    )
    kb_to_update = InlineKeyboardBuilder()
    kb_to_update.row(
        InlineKeyboardButton(
            text="Выключить отслеживание"
            if warehouse_information['warehouse']['is_active'] else "Включить отслеживание",
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
    await state.set_data(warehouse_information)
    return await callback.message.answer(
        f"Выбери, что желаешь изменить.\n"
        f"Сейчас у тебя: \n"
        f"Склад {warehouse_information['warehouse_name']} коэффициент: {warehouse_information['coefficient']} "
        f"с {warehouse_information['start_date']} до {warehouse_information['finish_date']}",
        reply_markup=kb_to_update.as_markup()
    )


@dp.callback_query(F.data.split('_')[0] == 'change')
@keyboard_work
async def
