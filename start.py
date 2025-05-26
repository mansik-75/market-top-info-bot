import json
from aiogram.types import Update
from bot import init_bot
from handlers import registration


bot, dp = init_bot()

dp.include_routers(registration.router)


async def process_event(event, dp):
    body = event.get('body')
    if body:
        update = Update(**json.loads(body))
        await dp.feed_update(bot, update)


async def start(event, context):
    print(event)
    await process_event(event, dp)
    return {'statusCode': 200, 'body': 'ok'}
