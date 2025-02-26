import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis


def init_bot():
    redis_connection = Redis(host=os.environ.get('REDIS_URL'), port=6379, db=0, password=os.environ.get('REDIS_PASSWORD'))
    state_storage = RedisStorage(redis_connection)
    bot = Bot(token=os.environ.get('API_TOKEN'))
    dp = Dispatcher(storage=state_storage)

    return bot, dp
