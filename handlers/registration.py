import datetime
import os

from aiogram import Bot, Router, F, types
from aiogram.filters import Command

from helper import *


router = Router()

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    chat_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    sheets_service = get_service()
    current_data = sheets_service.spreadsheets().values().get(
        spreadsheetId=os.environ.get('SPREADSHEET_ID'),
        range=f'Инфо!A:E',
    ).execute()
    values = current_data.get('values', [])
    start_row = len(values)
    _ = sheets_service.spreadsheets().values().append(
            spreadsheetId=os.environ.get('SPREADSHEET_ID'),
            range=f'Инфо!A{start_row + 1}:'
                  f'D{start_row + 1 + 1}',
            valueInputOption="USER_ENTERED",
            body={
                'values': [[datetime.datetime.now().strftime('%d.%m.%Y'), chat_id, f"@{username}", full_name]]
            },
        ).execute()

    return await message.answer(
        f'Привет 👋, {full_name}.\n\n'
        f'Для получения бесплатного внедрения сервиса необходимо пройти регистрацию.\n\n'
        f'Для этого поделитесь своими контактами с нашим ботом, нажав на кнопку отправки контактов ниже 👇',
        reply_markup=kb_get_contact(),
    )


@router.message(F.contact)
async def get_contact(message: types.Message):
    sheets_service = get_service()
    current_data: list[list] = sheets_service.spreadsheets().values().get(
        spreadsheetId=os.environ.get('SPREADSHEET_ID'),
        range=f'Инфо!A1:B'
    ).execute().get('values', [])
    k = 1
    for i in current_data:
        k += 1
        if i[1] == message.from_user.id:
            break
    if message.contact.user_id == message.from_user.id:
        await message.copy_to(os.environ.get('ADMIN_CHAT'))
        _ = sheets_service.spreadsheets().values().update(
            spreadsheetId=os.environ.get('SPREADSHEET_ID'),
            range=f'Инфо!E{k}:E{k}',
            valueInputOption="USER_ENTERED",
            body={
                'values': [[message.contact.phone_number]]
            },
        ).execute()
        await message.answer(f'Контакт получен, с вами свяжется менеджер!')
