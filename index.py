import json
import os
import datetime
import requests

update_ids = set()
TOKEN = os.environ.get('API_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')

def send_welcome(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {'chat_id': message['from']['id'], 'text': 'Добро пожаловать в бот MarketplaceInfoBot, я буду отправлять тебе информацию по заказам в твоём магазине.'}
    res1 = requests.post(url, data=data)
    print(res1)
    data_admin = {'chat_id': ADMIN_CHAT_ID, 'text': f"Новый пользователь желает присоединиться к рассылке\n\n chatId: {message['from']['id']}\n username: {message['from']['username']}"}
    res = requests.post(url, data=data_admin)
    print(res)
    data['text'] = 'Твой контакт отправлен администраторам, они с тобой свяжутся. Проверь, что твой username открыт для поиска в ТГ. Если нет, исправь и отправть еще раз /start'
    res2 = requests.post(url, data=data)
    print(res2)
    return res1


def handler(event, context):
    try:
        body = json.loads(event['body'])
        print(body)
        text = body['message'].get('text', False)
        if text == '/start':
            send_welcome(body['message'])
        print('success execution')
        return {'statusCode': 200, 'body': 'Message sent'}
    except Exception as err:
        print(err)
        return {'statusCode': 200, 'body': 'Some error'}

