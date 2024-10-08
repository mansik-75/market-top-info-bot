from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from helper import kb_markup_support, keyboard_work, ADMINS_ID, kb_menu

router = Router()


@router.message(Command('support'))
async def send_support_command(message: types.Message, state: FSMContext):
    return await send_support(message, state)


@router.callback_query(F.data == 'support')
@keyboard_work
async def send_support_callback(callback: types.CallbackQuery, state: FSMContext, *args, **kwargs):
    return await send_support(callback.message, state)


async def send_support(message: types.Message, state: FSMContext):
    await state.clear()
    return await message.answer(
        'Менеджер будет рад ответить на все вопросы!\n\n'
        'Чтобы помочь тебе быстрее, выбери, с чем возникли проблемы:',
        reply_markup=kb_markup_support.as_markup()
    )


@router.callback_query(F.data.in_(['support_manager', 'subscribe_issues']))
@keyboard_work
async def send_message_to_admin(call: types.CallbackQuery, bot: Bot, *args, **kwargs):
    text = f'От клиента @{call.message.chat.username}:\n\nПроблемы '
    if call.data == 'support_manager':
        text += 'требующие консультации с менеджером\n'
    elif call.data == 'subscribe_issues':
        text += 'с оплатой, необходимо срочно написать'
    await bot.send_message(chat_id=ADMINS_ID[0], text=text)
    return await call.message.answer(
        'Спасибо за помощь!\n\nЯ уже сообщил менеджеру, он свяжется с тобой в ближайшее время.',
        reply_markup=kb_menu.as_markup()
    )
