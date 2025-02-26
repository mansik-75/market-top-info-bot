from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_token_instruction() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(text='Инструкция по созданию токена', url='https://dev.wildberries.ru/openapi/api-information#tag/Avtorizaciya/Kak-sozdat-token')
    )
    return kb.as_markup()


def kb_token_type(marked={}) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=f"{'+ ' if marked.get('statistic', False) else ''}Статистика", callback_data='type__statistic'),
        InlineKeyboardButton(text=f"{'+ ' if marked.get('analytic', False) else ''}Аналитика", callback_data='type__analytic'),
        InlineKeyboardButton(text=f"{'+ ' if marked.get('promotion', False) else ''}Продвижение", callback_data='type__promotion'),
        InlineKeyboardButton(text=f"{'+ ' if marked.get('contant', False) else ''}Контент", callback_data='type__contant'),
        InlineKeyboardButton(text=f"{'+ ' if marked.get('price', False) else ''}Цены и скидки", callback_data='type__price'),
        InlineKeyboardButton(text=f"{'+ ' if marked.get('review', False) else ''}Вопросы и ответы", callback_data='type__review'),
        width=2,
    )
    kb.row(
        InlineKeyboardButton(text='Сохранить', callback_data='type__save')
    )
    kb.add(
        InlineKeyboardButton(text='Какие категории мне необходимы', url='ссылка на страницу telegraph, где показаны с какими методами работает сервис')
    )
    return kb.as_markup()


def kb_save() ->InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text='Сохранить', callback_data='save')
        InlineKeyboardButton(text='Отменить', callback_data='cancel'),
        width=2,
    )
    return kb.as_markup()
