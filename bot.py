import os

from aiogram import Bot, Dispatcher


def init_bot():
    bot = Bot(token=os.environ.get('API_TOKEN'))
    dp = Dispatcher()

    return bot, dp
