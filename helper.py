import json
import os

import boto3
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


from google.oauth2 import service_account
from googleapiclient.discovery import build


boto_session = boto3.session.Session(
    aws_access_key_id=os.environ.get('KEY_ID'),
    aws_secret_access_key=os.environ.get('SECRET')
)
s3 = boto_session.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    region_name='ru-central1',
)
s3_bucket = os.environ.get('S3_BUCKET')

creds = json.loads(s3.get_object(Bucket=s3_bucket, Key='credentials.json')['Body'].read())



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


def get_service():
    credentials = service_account.Credentials.from_service_account_info(
        creds
    )
    service = build('sheets', 'v4', credentials=credentials)
    return service
