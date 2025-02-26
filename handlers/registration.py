
import re
from aiogram import Bot, Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from helper import *
from states import DownloadAPIKey


router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(DownloadAPIKey.key)
    # регистрация пользователя в системе, тип не активный
    # await state.set_data({'username': message.from_user.username, 'name': message.from_user.full_name, 'user_id': message.from_user.id})
    return await message.answer(f'Привет, {message.from_user.full_name} добро пожаловать. Пришли API ключ', reply_markup=kb_token_instruction())


@router.message(DownloadAPIKey.key)
async def api_key_handler(message: types.Message, state: FSMContext):
    api_key = message.text
    re_sub = r"^([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_\-\+\/=]*)"
    if not re.match(re_sub, api_key):
        return await message.answer('Ты прислал неправильный API токен, проверь еще раз', reply_markup=kb_token_instruction())
    await state.set_state(DownloadAPIKey.key_type)
    # отправка токена пользователя
    # await state.set_data(dict(**state_data, token=api_key))
    return await message.answer('Теперь выбери, какие показатели ты хочешь отслеживать: ', reply_markup=kb_token_type())


@router.callback_query(F.data.startswith('type'))
async def proccess_set_token_type(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    callback_data = callback.data.split('__')[1:]
    state_data = await state.get_data()
    if callback_data == 'save':
        # если пусто, спросить выбрал ли он все правильно
        await state.set_state(DownloadAPIKey.key_type_save)
        return await callback.message.answer(f"Ты выбрал такое: ... . Сохранить?", reply_markup=kb_save())
    if callback_data not in state_data.keys():
        state_data[callback_data] = True
    else:
        state_data.pop(callback_data)
    return await callback.message.edit_reply_markup(reply_markup=kb_token_type(state_data))


@router.callback(DownloadAPIKey.key_type_save)
async def save_token_type(callback: types.Callback, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    state_data = await state.get_data()
    if callback.data == 'save':
        # отправить на сервер данные о пользовательском выборе
        await state.clear()
        await state.set_state(DownloadAPIKey.email)
        return await callback.message.answer('Твой выбор сохранен. Теперь отправь свою почту, на которую нужно выдать доступ к таблицам')
    return callback.message.answer("Хорошо, выбери что ты хочешь отслеживать", reply_markup=kb_token_type(state_data))


@router.message(DownloadAPIKey.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text
    # отправить на серевер почту пользователя
    await state.clear()
    return await message.answer("Мы получили все твои данные, для дальнейшей работы с тобой свяжется менеджер")
