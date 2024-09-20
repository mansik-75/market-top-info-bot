import datetime
import json
import os

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.methods import SendInvoice

from helper import kb_markup_subscribe, kb_markup_subscribe_tariff, PRICE_IDS, PRICES, ADMINS_ID, make_request, \
    keyboard_work

router = Router()


@router.message(Command('subscription'))
async def subscribe_status_command(message: types.Message, state: FSMContext):
    return await subscribe_status(message, state)


@router.callback_query(F.data == 'subscribe_status')
@keyboard_work
async def subscribe_status_callback(callback: types.CallbackQuery, state: FSMContext):
    return await subscribe_status(callback.message, state)


async def subscribe_status(message: types.Message, state: FSMContext):
    await state.clear()
    answer = await make_request(
        url='/users',
        params={'chat_id': message.chat.id},
        method='get'
    )
    if not answer:
        await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой')
        return
    if answer['success']:
        subscribe_exp_date = answer['subscribe_exp']
        if answer['active']:
            await message.answer(
                f"Подписка действительна до "
                f"{datetime.datetime.strptime(subscribe_exp_date, '%Y-%m-%d').strftime('%d.%m.%Y')}"
            )
        else:
            await message.answer(
                'Сейчас у тебя нет действующих подписок, можешь купить',
                reply_markup=kb_markup_subscribe.as_markup()
            )
    else:
        await message.answer(
            'Сейчас у тебя нет действующих подписок, можешь купить',
            reply_markup=kb_markup_subscribe.as_markup()
        )


@router.callback_query(F.data == 'subscribe_pay')
async def send_keyboard_with_tariffs(callback: types.CallbackQuery):
    await callback.message.answer(
        'Выберите тариф, который хотите оплатить',
        reply_markup=kb_markup_subscribe_tariff.as_markup()
    )


@router.callback_query(F.data.in_(PRICE_IDS))
@keyboard_work
async def subscribe_payment(callback: types.CallbackQuery):
    """Метод, который отправляет счет пользователю"""
    if os.environ.get('PAYMENT_TOKEN').split(':')[1] == 'TEST':
        await callback.message.answer(
            'Это тестовый вариант оплаты, так что нужно использовать тестовую карту с реквизитами 1111 1111 1111 1026'
        )
    price = int(PRICES[callback.data].amount)
    return SendInvoice(
        chat_id=callback.message.chat.id,
        title='Подписка на бота',
        description='Вы оплачиваете подписку на месяц на пользование ботом для составления отчетов по продажам WB',
        provider_token=os.environ.get('PAYMENT_TOKEN'),
        currency='rub',
        is_flexible=False,
        prices=[PRICES[callback.data]],
        start_parameter='service-subscription',
        payload=f'subscription-for-user_{callback.message.chat.id}',
        need_email=True,
        need_phone_number=True,
        send_email_to_provider=True,
        send_phone_number_to_provider=True,
        provider_data=json.dumps(
            {
                'receipt': {
                    'items': [
                        {
                            'description': 'оплата подписки market.top',
                            'quantity': '1.00',
                            'amount': {
                                'value': "{0:.2f}".format(price / 100),
                                'currency': 'RUB'
                            },
                            'vat_code': 1
                        }
                    ]
                }
            }
        )
    )


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    """Метод, который занимается проверкой правильности заполнения счета пользователем"""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    """Метод, который вызывается после успешной оплаты и регистрирует пользователя на сервере"""
    payload = message.successful_payment.invoice_payload
    chat_id = message.chat.id
    username = message.chat.username
    order_info = message.successful_payment.order_info
    print(payload)
    answer = await make_request(
        url='/users',
        params={'chat_id': ADMINS_ID[0]},
        json_data={
            'chat_id': chat_id,
            'username': username,
            'phone_number': order_info.phone_number,
            'email': order_info.email,
            'total_amount': message.successful_payment.total_amount,
        },
    )
    print(answer)
    if not (answer and answer['success']):
        await message.answer(
            f'Произошла ошибка, пожалуйста, свяжитесь с поддержкой, указав следующие данные: '
            f'{chat_id} и {message.successful_payment.provider_payment_charge_id}'
        )
        return
    text = f'Поздравляю с оформлением тарифа!'
    return await message.answer(text)
