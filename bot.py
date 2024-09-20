import asyncio
import datetime
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis import Redis

import subscribe_payment
import support
from helper import kb_markup_subscribe, make_request, keyboard_work, kb_menu, kb_wrong_token, \
    kb_confirm_adding_warehouse, kb_warehouse_setting_menu, create_update_keyboard, all_warehouses_buttons, \
    fill_kb_all_warehouses, all_warehouses_names, validate
from states import AddToken, AddWarehouse, ChangeWarehouse

# redis_connection = Redis(host=os.environ.get('REDIS_URL'), port=6379, db=0, password=os.environ.get('REDIS_PASSWORD'))
# state_storage = RedisStorage(redis_connection)
state_storage = MemoryStorage()
update_ids = set()


bot = Bot(token=os.environ.get('API_TOKEN'))
dp = Dispatcher(storage=state_storage)
dp.include_routers(subscribe_payment.router, support.router)


@dp.message(Command('start'))
async def send_welcome(message: types.Message, state):
    await state.clear()
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
    return await message.answer(
        'Я могу уведомлять тебя о наличии бесплатной приемки товара на WB.'
        'Если хочешь точно отслеживать коэффициенты, отправь мне WB API токен для поставок',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_menu.as_markup()
    )


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
@dp.callback_query(F.data == 'cancel_agree')
@dp.callback_query(F.data == 'warehouse_settings')
@keyboard_work
async def finish_token_adding(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.data == 'token_no' or callback.data == 'warehouse_settings':
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
        d = {'sheet': 0, 'data': warehouses['data']}
        await state.set_data(d)
        for warehouse in warehouses['data'][d['sheet'] * 10:(d['sheet'] + 1) * 10]:
            kb_warehouses.button(
                text=f"{warehouse['warehouse_name']} "
                     f"коэффициент: {warehouse['coefficient']} "
                     f"с {warehouse['start_date']} до {warehouse['finish_date']}",
                callback_data=f"warehouse_update__{warehouse['id']}"
            )
        kb_warehouses.adjust(1)
        kb_warehouses.row(
            InlineKeyboardButton(text='< сюда', callback_data='update_warehouse_list__previous'),
            InlineKeyboardButton(text='> туда', callback_data='update_warehouse_list__next')
        )
        return await callback.message.answer(
            'Итак, выбери какой склад желаешь изменить',
            reply_markup=kb_warehouses.as_markup()
        )
    elif callback.data == 'warehouse_add':
        await state.set_state(AddWarehouse.name)
        d = {'sheet': 0}
        await state.set_data(d)
        kb_all_warehouses = fill_kb_all_warehouses(d['sheet'])
        return await callback.message.answer('Выберите из списка склад', reply_markup=kb_all_warehouses.as_markup())


@dp.callback_query(F.data.split('__')[0] == 'update_warehouse_list')
@keyboard_work
async def update_warehouse_manager(callback: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    text = 'Итак, выбери какой склад желаешь изменить'
    if callback.data == 'update_warehouse_list__previous':
        d['sheet'] -= 1
        if d['sheet'] < 0:
            text += '\nЭто первая страница'
            d['sheet'] = 0
    elif callback.data == 'update_warehouse_list__next':
        d['sheet'] += 1
        if d['sheet'] > len(all_warehouses_buttons) // 10:
            text += '\nЭто последняя страница'
            d['sheet'] = len(all_warehouses_buttons) // 10
    kb_warehouses = InlineKeyboardBuilder()
    for warehouse in d['data']:
        kb_warehouses.button(
            text=f"{warehouse['warehouse_name']} "
                 f"коэфф: {warehouse['coefficient']} "
                 f"с {warehouse['start_date']} до {warehouse['finish_date']}",
            callback_data=f"warehouse_update__{warehouse['id']}"
        )
    kb_warehouses.adjust(1)
    kb_warehouses.row(
        InlineKeyboardButton(text='< сюда', callback_data='update_warehouse_list__previous'),
        InlineKeyboardButton(text='> туда', callback_data='update_warehouse_list__next')
    )
    await state.set_data(d)
    return await callback.message.answer(
        text,
        reply_markup=kb_warehouses.as_markup()
    )


@dp.callback_query(F.data.split('__')[0] == 'warehouse_list')
@keyboard_work
async def all_warehouses_manager(callback: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    text = 'Выберите из списка склад'
    if callback.data == 'warehouse_list__previous':
        d['sheet'] -= 1
        if d['sheet'] < 0:
            text += '\nЭто первая страница'
            d['sheet'] = 0
    elif callback.data == 'warehouse_list__next':
        d['sheet'] += 1
        if d['sheet'] > len(all_warehouses_buttons) // 9:
            text += '\nЭто последняя страница'
            d['sheet'] = len(all_warehouses_buttons) // 9
    kb_warehouses = fill_kb_all_warehouses(d['sheet'])
    await state.set_data(d)
    return await callback.message.answer(
        text,
        reply_markup=kb_warehouses.as_markup()
    )


@dp.callback_query(AddWarehouse.name)
@keyboard_work
async def fill_warehouse_name(callback: types.CallbackQuery, state: FSMContext):
    warehouse_id = callback.data
    warehouse_name = all_warehouses_names[warehouse_id]
    await state.set_data({'warehouse_name': warehouse_name, 'warehouse_id': warehouse_id})
    await state.set_state(AddWarehouse.coefficient)
    return await callback.message.answer('Отправь коэффициент, ниже которого тебя необходимо уведомлять, например 5')


@dp.message(AddWarehouse.coefficient)
async def fill_coefficient(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        coefficient = int(message.text)
    except ValueError:
        return await message.answer('Необходимо ввести коэффициент в виде числа, например, 5')
    data['coefficient'] = coefficient
    await state.set_data(data)
    if 'start_date' in data:
        return await message.answer(
            f"Ты хочешь добавить склад {data['warehouse_name']}\n"
            f"с коэффициентом {data['coefficient']}\n"
            f"на даты с {data['start_date']}\n"
            f" по {data['finish_date']}?",
            reply_markup=kb_confirm_adding_warehouse.as_markup()
        )
    await state.set_state(AddWarehouse.interval)
    return await message.answer(
        'Осталось совсем чуть-чуть, отправь интервал дат, в которые ты хочешь, чтобы я следил за поставками.\n\n '
        'Например 01.01.2024 - 15.01.2024'
    )


@dp.message(AddWarehouse.interval)
async def fill_start_and_finish_date_and_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        start_date, finish_date = message.text.split(' - ')
        validate(start_date, "%d.%m.%Y")
        validate(finish_date, "%d.%m.%Y")
    except ValueError:
        return await message.answer('Необходимо следовать примеру при добавлении даты. Пример: 01.01.2024 - 15.01.2024')
    except TypeError:
        return message.answer('Необходимо ввести дату в формате ДД.ММ.ГГГГ. Пример: 01.01.2024 - 15.01.2024')
    data.update(start_date=start_date, finish_date=finish_date)
    await state.set_data(data)
    await state.set_state(AddWarehouse.confirm)
    return await message.answer(
        f"Ты хочешь добавить склад {data['warehouse_name']}\n"
        f"с коэффициентом {data['coefficient']}\n"
        f"на даты с {data['start_date']}\n"
        f" по {data['finish_date']}?",
        reply_markup=kb_confirm_adding_warehouse.as_markup()
    )


@dp.callback_query(F.data == 'save')
@keyboard_work
async def save_warehouse(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    data['start_date'] = datetime.datetime.strptime(data['start_date'], "%d.%m.%Y").strftime("%Y-%m-%d")
    data['finish_date'] = datetime.datetime.strptime(data['finish_date'], "%d.%m.%Y").strftime("%Y-%m-%d")
    answer = await make_request(
        url='/supplies/warehouses',
        params={'chat_id': callback.message.chat.id},
        json_data=[data],
    )
    print(answer)
    return await callback.message.answer('Отлично, склад добавлен в отслеживание', reply_markup=kb_menu.as_markup())


@dp.callback_query(F.data == 'change_coefficient_adding')
@keyboard_work
async def change_coefficient_adding(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddWarehouse.coefficient)
    return await callback.message.answer('Отправь коэффициент, ниже которого тебя необходимо уведомлять, например 5')


@dp.callback_query(F.data == 'change_dates_adding')
@keyboard_work
async def change_interval_adding(callback: types.CallbackQuery, state: FSMContext):
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
    kb_to_update = create_update_keyboard(warehouse_id, warehouse_information['warehouse'])
    await state.set_data(warehouse_information['warehouse'])
    return await callback.message.answer(
        f"Выбери, что желаешь изменить.\n"
        f"Сейчас у тебя: \n"
        f"Склад: {warehouse_information['warehouse']['warehouse_name']}\n"
        f" коэффициент: {warehouse_information['warehouse']['coefficient']}\n"
        f"с {warehouse_information['warehouse']['start_date']}\n"
        f" до {warehouse_information['warehouse']['finish_date']}",
        reply_markup=kb_to_update.as_markup()
    )


@dp.callback_query(F.data.split('__')[0] == 'change_is_active')
@keyboard_work
async def update_activity(callback: types.CallbackQuery, state: FSMContext):
    warehouse_info = await state.get_data()
    warehouse_info['is_active'] = not warehouse_info['is_active']
    text = "Хорошо, не буду отслеживать этот склад" if not warehouse_info['is_active'] \
        else "Добавил склад на отслеживание, лови вкусные коэффициенты"
    await state.set_data(warehouse_info)
    return await callback.message.answer(
        f"{text}\n\n"
        f"Сейчас у тебя:\n"
        f"Склад: {warehouse_info['warehouse_name']}\n"
        f" коэффициент: {warehouse_info['coefficient']}\n"
        f"с {warehouse_info['start_date']}\n"
        f" до {warehouse_info['finish_date']}",
        reply_markup=create_update_keyboard(warehouse_info['id'], warehouse_info).as_markup()
    )


@dp.callback_query(F.data.split('__')[0] == 'change_coefficient')
@keyboard_work
async def update_coefficient_set_state(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChangeWarehouse.coefficient)
    return await callback.message.answer(
        'Введи коэффициент, ниже которого хочешь получать уведомления об открытой приемке\n'
        'Например, 5'
    )


@dp.message(ChangeWarehouse.coefficient)
async def update_coefficient(message: types.Message, state: FSMContext):
    warehouse_info = await state.get_data()
    try:
        new_value = int(message.text)
    except ValueError:
        return await message.answer('Необходимо ввести коэффициент в виде числа')
    await state.clear()
    warehouse_info['coefficient'] = new_value
    await state.set_data(warehouse_info)
    return await message.answer(
        f"Коэффициент изменен на {new_value}\n\n"
        f"Сейчас у тебя:\n"
        f"Склад: {warehouse_info['warehouse_name']}\n"
        f" коэффициент: {warehouse_info['coefficient']}\n"
        f" с {warehouse_info['start_date']}\n"
        f" до {warehouse_info['finish_date']}",
        reply_markup=create_update_keyboard(warehouse_info['id'], warehouse_info).as_markup()
    )


@dp.callback_query(F.data.split('__')[0] == 'change_interval')
@keyboard_work
async def update_interval_set_state(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChangeWarehouse.interval)
    return await callback.message.answer(
        "Введи новый интервал, внутри которого я буду уведомлять тебя об открытых складах на поставку\n"
        "Например, 01.01.2024 - 04.01.2024"
    )


@dp.message(ChangeWarehouse.interval)
async def update_intervals(message: types.Message, state: FSMContext):
    warehouse_info = await state.get_data()
    try:
        new_start_date, new_finish_date = message.text.split(' - ')
        validate(new_start_date, "%d.%m.%Y")
        validate(new_finish_date, "%d.%m.%Y")
    except ValueError:
        return await message.answer('Необходимо следовать примеру при добавлении даты. Пример: 01.01.2024 - 15.01.2024')
    except TypeError:
        return message.answer('Необходимо ввести дату в формате ДД.ММ.ГГГГ. Пример: 01.01.2024 - 15.01.2024')
    warehouse_info['start_date'] = new_start_date
    warehouse_info['finish_date'] = new_finish_date
    await state.clear()
    await state.set_data(warehouse_info)
    return await message.answer(
        f"Принял, буду тебя уведомлять о подходящих коэффициентах приемки в период "
        f"с {new_start_date} по {new_finish_date}\n\n"
        f"Сейчас у тебя:\n"
        f"Склад: {warehouse_info['warehouse_name']}\n"
        f" коэффициент: {warehouse_info['coefficient']}\n"
        f"с {warehouse_info['start_date']}\n"
        f" до {warehouse_info['finish_date']}",
        reply_markup=create_update_keyboard(warehouse_info['id'], warehouse_info).as_markup()
    )


@dp.callback_query(F.data == 'change_save')
@keyboard_work
async def save_change_answer(callback: types.CallbackQuery, state: FSMContext):
    warehouse_info = await state.get_data()
    kb_answer_save = InlineKeyboardBuilder()
    kb_answer_save.row(
        InlineKeyboardButton(
            text="Да, подтверждаю",
            callback_data="save_agree"
        ),
        InlineKeyboardButton(
            text="Нет, хочу ещё что-то изменить",
            callback_data="save_disagree"
        )
    )
    return await callback.message.answer(
        f"Ты выбрал сохранить изменения\n"
        f"Сейчас у тебя:\n"
        f"Склад: {warehouse_info['warehouse_name']}\n"
        f" коэффициент: {warehouse_info['coefficient']}\n "
        f"с {warehouse_info['start_date']}\n"
        f" до {warehouse_info['finish_date']}",
        reply_markup=kb_answer_save.as_markup()
    )


@dp.callback_query(F.data == 'save_agree')
@dp.callback_query(F.data == 'save_disagree')
@keyboard_work
async def save_change_process(callback: types.CallbackQuery, state: FSMContext):
    warehouse_info = await state.get_data()
    if callback.data == 'save_disagree':
        return await callback.message.answer(
            f"Выбери, что желаешь изменить"
            f"Сейчас у тебя:\n"
            f"Склад: {warehouse_info['warehouse_name']}\n"
            f" коэффициент: {warehouse_info['coefficient']}\n"
            f"с {warehouse_info['start_date']}\n"
            f" до {warehouse_info['finish_date']}",
            reply_markup=create_update_keyboard(warehouse_info['id'], warehouse_info).as_markup()
        )

    warehouse_info['start_date'] = datetime.datetime.strptime(warehouse_info['start_date'], "%d.%m.%Y").strftime("%Y-%m-%d")
    warehouse_info['finish_date'] = datetime.datetime.strptime(warehouse_info['finish_date'], "%d.%m.%Y").strftime("%Y-%m-%d")

    response = await make_request(
        url="/supplies/warehouses/update",
        params={'chat_id': callback.message.chat.id},
        json_data=[warehouse_info]
    )
    print(response)
    if response['success']:
        await state.clear()
        return await callback.message.answer(
            "Приступаю к отслеживанию приемок",
            reply_markup=kb_menu.as_markup()
        )


@dp.callback_query(F.data == 'change_cancel')
@keyboard_work
async def cancel_change_answer(callback: types.CallbackQuery, state: FSMContext):
    warehouse_info = await state.get_data()
    warehouse_info_old = await make_request(
        url=f"/supplies/warehouses/{warehouse_info['id']}",
        params={'chat_id': callback.message.chat.id},
        method='get'
    )
    kb_answer_cancel = InlineKeyboardBuilder()
    kb_answer_cancel.row(
        InlineKeyboardButton(
            text="Да, подтверждаю",
            callback_data="cancel_agree"
        ),
        InlineKeyboardButton(
            text="Нет, хочу ещё что-то изменить",
            callback_data="cancel_disagree"
        )
    )
    old_info = warehouse_info_old['warehouse']
    return await callback.message.answer(
        "Действительно желаешь отменить изменения, все изменения не сохранятся\n"
        f"Сейчас у тебя:\n"
        f"Склад: {warehouse_info['warehouse_name']}\n"
        f"коэффициент: {warehouse_info['coefficient']} <s>({old_info['coefficient']})</s>\n"
        f"с {warehouse_info['start_date']} <s>({old_info['start_date']})</s>\n"
        f"до {warehouse_info['finish_date']} <s>({old_info['finish_date']})</s>",
        reply_markup=kb_answer_cancel.as_markup(),
        parse_mode='HTML'
    )


@dp.callback_query(F.data == 'cancel_disagree')
@keyboard_work
async def cancel_change_process(callback: types.CallbackQuery, state: FSMContext):
    warehouse_info = await state.get_data()
    return await callback.message.answer(
        f"Выбери, что желаешь изменить"
        f"Сейчас у тебя:\n"
        f"Склад: {warehouse_info['warehouse_name']}\n"
        f" коэффициент: {warehouse_info['coefficient']}\n"
        f"с {warehouse_info['start_date']}\n"
        f" до {warehouse_info['finish_date']}",
        reply_markup=create_update_keyboard(warehouse_info['id'], warehouse_info).as_markup()
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
