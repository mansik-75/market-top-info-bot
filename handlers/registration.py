import os

from aiogram import Bot, Router, F, types
from aiogram.filters import Command

from helper import *

router = Router()

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    # регистрация пользователя в системе, тип не активный
    # await state.set_data({'username': message.from_user.username, 'name': message.from_user.full_name, 'user_id': message.from_user.id})
    return await message.answer(
        f'Привет, {message.from_user.full_name}.\n'
        f'Я твой бот, который поможет тебе узнать больше о своем магазине и увеличить выручку.\n'
        f'Давай познакомимися, пришли свой контакт',
        reply_markup=kb_get_contact(),
    )


@router.message(F.contact)
async def get_contact(message: types.Message, bot: Bot):
    if message.contact.user_id == message.from_user.id:
        await message.copy_to(os.environ.get('ADMIN_CHAT'))
        await message.answer(f'Контакт получен, с вами свяжется менеджер!')
