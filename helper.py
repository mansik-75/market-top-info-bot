from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def kb_token_instruction() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(
        types.InlineKeyboardButton(text='Инструкция по созданию токена', url='https://dev.wildberries.ru/openapi/api-information#tag/Avtorizaciya/Kak-sozdat-token')
    )
    return kb.as_markup()


def kb_get_contact() -> types.ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(
        types.KeyboardButton(text='Отправить контакт', request_contact=True)
    )
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)
