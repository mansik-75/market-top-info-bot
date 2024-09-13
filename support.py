from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.methods import SendMessage

from helper import kb_markup_support, keyboard_work, ADMINS_ID

router = Router()


@router.message(Command('support'))
async def send_support(message: types.Message, state):
    await state.finish()
    await message.answer(
        'Менеджер будет рад ответить на все вопросы!\n\n'
        'Чтобы помочь тебе быстрее, выбери, с чем возникли проблемы:',
        reply_markup=kb_markup_support.as_markup()
    )


@router.callback_query(F.data in ['support_manager'])
@keyboard_work
async def send_message_to_admin(call: types.CallbackQuery):
    text = f'От клиента @{call.message.chat.username}:\n\nПроблемы '
    if call.data == 'support_manager':
        text += 'требующие консультации с менеджером\n'
    await SendMessage(chat_id=ADMINS_ID[0], text=text)
    await call.message.answer('Спасибо за помощь!\n\nЯ уже сообщил менеджеру, он свяжется с тобой в ближайшее время.')
