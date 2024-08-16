import os
import io
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiohttp import ClientSession
from datetime import datetime
import json


from states import (GenerateFullUnitEconomy, Advertisement, CostPrices,
                    GetUnitEconomy, GetOPI, OtherInformation, SelfPayments,
                    WbDetailsState, DownloadСheque, DownloadFirstTime, 
                    WritePromoCode, WriteTaxRate, Questions)
from helper import (kb_markup_start, kb_markup_get_first_time, kb_markup_download_opi,
                    kb_markup_download_unit, kb_markup_subscribe,
                    kb_markup_subscribe_tariff, kb_markup_download_ads,
                    kb_markup_download_other_expenses, kb_markup_download_selfs,
                    kb_download_extra_report, kb_lifetime_error, kb_brand_count_error,
                    kb_change_cost_price, kb_back, kb_markup_first,
                    kb_markup_support, kb_markup_new_costs, kb_markup_items_without_costs, 
                    kb_markup_find_report)
from helper import PRICE_IDS, PRICES


ADMINS_ID = [526206350, 426131335, 53060580]
state_storage = RedisStorage2(os.environ.get('REDIS_URL'), 6379, db=0, password=os.environ.get('REDIS_PASSWORD'))
update_ids = set()


async def process_event(update, dp: Dispatcher):
    Bot.set_current(dp.bot)
    update = types.Update.to_object(update)
    await dp.process_update(update)
    return await return_answer()

async def return_answer():
    return {
        'statusCode': 200,
        'body': 'ok'
    }

async def start(event, context):
    print(event)
    print(update_ids)
    update = json.loads(event['body'])
    update_id = update['update_id']
    print(update_id)

    if update_id in update_ids:
        return {
            'statesCode': 200,
            'body': 'not ok'
        }

    update_ids.add(update_id)

    loop = asyncio.get_event_loop()
    bot = Bot(token=os.environ.get('API_TOKEN'))
    dp = Dispatcher(bot, storage=state_storage, loop=loop)


    def keyboard_work(function):
        async def decorator(call, state):
            await bot.answer_callback_query(call.id)
            answer = await function(call, state)
            try:
                await call.message.edit_reply_markup()
            except MessageNotModified:
                pass
            return answer
        return decorator

    def check_date(function):
        async def decorator(message, state):
            date = message.text
            try:
                new_date = datetime.strptime(date, "%d.%m.%Y").date()
            except ValueError as e:
                await message.answer('Вы ввели неправильную дату, пожалуйста введите её в формате дд.мм.гггг')
                return
            return await function(message, state, date)
        return decorator

    async def make_request(url, params: dict, json_data=None, files=None, method='post'):
        session = ClientSession(trust_env=True)
        url = os.environ.get('API_URL') + url
        if method == 'post':
            async with session.post(url=url, params=params, json=json_data, data=files) as response:
                print(response.status)
                if response.status < 500:
                    answer = await response.json()
                else:
                    answer = False
        else:
            async with session.get(url=url, params=params) as response:
                print(response.text)
                if response.status < 500:
                    answer = await response.json()
                else:
                    answer = False
        print(answer)
        await session.close()
        return answer

    def get_basket_by_sku(sku):
        baskets = {
            (0, 14400000): '01',
            (14400000, 28800000): '02',
            (28800000, 43200000): '03',
            (43200000, 72000000): '04',
            (72000000, 100800000): '05',
            (100800000, 106200000): '06',
            (106200000, 111600000): '07',
            (111600000, 117000000): '08',
            (117000000, 131400000): '09',
            (131400000, 160200000): '10',
            (160200000, 165600000): '11'
        }
        for i in baskets:
            if sku in range(*i):
                return baskets[i]
        return '12'

    def check_state_exist(function):
        async def decorator(message, state):
            """Удаляет данные с предыдущего шага и отправляет пользователя на прошлый пункт"""
            current_state_json = await make_request(
                url='/back/current',
                params={'chat_id': message.chat.id},
                method='get',
            )
            if not current_state_json['success']:
                return await message.answer(current_state_json['error'])
            current_state = current_state_json['last_downloaded']
            print(current_state)
            call = await function(message, state, current_state)
            delete_last = await make_request(
                url='/back/delete-last',
                params={'chat_id': message.chat.id}
            )
            return call
        return decorator


    @dp.message_handler(commands=['start', 'report'], state='*')
    async def send_welcome(message: types.Message, state):
        await state.finish()
        answer = await make_request(
            url='/start',
            params={'chat_id': message.chat.id},
            json_data={
                'chat_id': message.chat.id,
                'username': message.chat.username,
            }            
        )
        if not answer['success']:
            answer = await make_request(
                url='/users',
                params={'chat_id': message.chat.id},
                method='get'
            )
            if not answer['success']:
                await message.answer('Ваша подписка просрочена', reply_markup=kb_markup_subscribe)
                return
            if answer['is_first_time']:
                downloaded_data = await make_request(
                    url='/downloads',
                    params={'chat_id': message.chat.id},
                    method='get',
                )
                if not downloaded_data['seller_url']:
                    await message.answer('*ДАВАЙ НАЧНЕМ!* Отправь *ссылку на любой свой товар или его артикул*, и я начну анализировать весь твой магазин.',
                        parse_mode=types.message.ParseMode.MARKDOWN,
                        reply_markup=kb_back
                    )
                    await state.set_state(DownloadFirstTime.download_seller_url.state)
                    return
                await state.set_state(WbDetailsState.download_wb_details.state)
                await message.answer('Первый шаг к получению отчетов уже сделан, теперь загрузи *файл детализации*', parse_mode=types.message.ParseMode.MARKDOWN)
                return await message.answer('*Где найти детализацию*?\n- личный кабинет селлера\n- раздел «Финансовые отчеты»\n- детализация\n- скачать детализацию\n\n' \
                            'У меня есть подробная *инструкция* со скриншотами для тебя! Переходи по [ссылке](https://docs.google.com/document/d/19wpRwXf3muZBORlH6IRjtfA8QdGEMeyH_GPwa__BXB4/edit?pli=1), ' \
                            'чтобы правильно загрузить детализацию\n', disable_web_page_preview=True, parse_mode=types.message.ParseMode.MARKDOWN)

        else:
            await message.answer('Мой создатель – селлер с ежемесячным оборотом на WB более 120 млн рублей в месяц.  Я знаю, как поднять твою прибыль на WB и выйти в TOP в твоей категории.\n\n' \
                                'Для этого, в первую очередь, нужно *правильно считать и анализировать финансовые показатели*, учитывая потери, браки, рекламные расходы, себестоимость и многое другое. ' \
                                'Все эти расчеты я сделаю вместо тебя с точностью до копейки и подскажу, как поднять прибыль.\n\n' \
                                'Ниже я отправил примеры отчетов, которые ты можешь получить по своему магазину уже через 15-20 минут. Это:\n' \
                                '1) *ОПиУ (P&L)* – отчет о прибылях и убытках, показывает финансовый результат бизнеса;\n' \
                                '2) *Юнит-Экономика* – отчет, который показывает прибыль по каждому отдельному товару.', parse_mode=types.message.ParseMode.MARKDOWN)
            req = await make_request(
                url='/first/send-photos',
                params={'chat_id': message.chat.id},
                method='get'
            )
            await message.answer('Получи свой первый финансовый отчет совершенно *бесплатно* и узнай, как увеличить прибыль.\n\n' \
                                '_Расчетное время получения отчета: 15-20 минут_', parse_mode=types.message.ParseMode.MARKDOWN)
            await state.set_state(DownloadFirstTime.download_seller_url.state)
            await message.answer('*ДАВАЙ НАЧНЕМ!* Отправь *ссылку на любой свой товар или его артикул*, и я начну анализировать весь твой магазин.',
                parse_mode=types.message.ParseMode.MARKDOWN,
                reply_markup=kb_back
            )
            return
        await state.set_state(WbDetailsState.download_wb_details.state)
        await message.answer('Уже бегу составлять отчеты! С тебя *файл детализации*, отправь его мне в формате xslx или zip.', parse_mode=types.message.ParseMode.MARKDOWN, reply_markup=kb_markup_find_report)


    @dp.message_handler(state=DownloadFirstTime.download_seller_url)
    async def download_seller_url(message: types.Message, state: FSMContext):
        sku = message.text
        pattern = r"\w+://www\.wildberries\.ru/catalog/(\d*)/.*"
        if sku.isdigit():
            sku = int(sku)
        else:
            match = re.fullmatch(pattern, sku)
            if match:
                correct = re.findall(pattern, sku)
                sku = int(correct[0])
            else:
                await message.answer('Введите корректную ссылку на товар или его артикул')
                return

        uri = f"https://basket-{get_basket_by_sku(sku)}.wb.ru/vol{sku // 100_000}/part{sku // 1000}/{sku}/info/ru/card.json"

        print(uri)

        async with ClientSession(trust_env=True) as session:
            async with session.get(url=uri) as response:
                print(response.status)
                if response.status != 200:
                    await message.answer('Данного товара не существует, пожалуйста проверьте корректность ссылки или его артикул')
                    return
                json_response = await response.json()
                seller_id = json_response['selling'].get('supplier_id')
                if not seller_id:
                    await message.answer('Данного товара не существует, пожалуйста проверьте корректность ссылки или его артикул')
                    return
            async with session.get(f'https://www.wildberries.ru/webapi/seller/data/short/{seller_id}') as response:
                print(response.status)
                json_response = await response.json()
                if response.status != 200 or json_response['isUnknown']:
                    return await message.answer('Данный товар не представлен на WB, пожалуйста, скинь действительную ссылку')
                seller_name = json_response.get('trademark', json_response['name'])

        answer = await make_request(
            url='/first/seller-info',
            params={'chat_id': message.chat.id},
            json_data={
                'seller_item_sku': sku,
                'seller_name': seller_name,
                'seller_id': seller_id,
            }
        )
        await message.answer('Отчеты скоро будут готовы!\n\n'
                             'Для этого загрузи в бот *детализацию из личного кабинета WB* за последнюю неделю (1 файл в формате xslx или zip)', parse_mode=types.message.ParseMode.MARKDOWN)
        await message.answer('*Где найти детализацию*?\n- личный кабинет селлера\n- раздел «Финансовые отчеты»\n- детализация\n- скачать детализацию\n\n' \
                             'У меня есть подробная *инструкция* со скриншотами для тебя! Переходи по [ссылке](https://docs.google.com/document/d/19wpRwXf3muZBORlH6IRjtfA8QdGEMeyH_GPwa__BXB4/edit?pli=1), ' \
                             'чтобы правильно загрузить детализацию\n', disable_web_page_preview=True, parse_mode=types.message.ParseMode.MARKDOWN)
        await state.finish()
        await state.set_state(WbDetailsState.download_wb_details.state)

    @dp.message_handler(commands=['support'], state='*')
    async def send_support(message: types.Message, state):
        await state.finish()
        await message.answer('Менеджер будет рад ответить на все вопросы!\n\nЧтобы помочь тебе быстрее, выбери, с чем возникли проблемы:', reply_markup=kb_markup_support)

    @dp.callback_query_handler(lambda c: c.data in ['support_report', 'support_pattern', 'support_fill', 'support_pnl', 'support_sub', 'support_work', 'support_manager'], state='*')
    @keyboard_work
    async def send_message_to_admin(call: types.CallbackQuery, state: FSMContext):
        text = f'От клиента @{call.message.chat.username}:\n\nПроблемы '
        if call.data == 'support_report':
            text += 'с загрузкой детализации\n'
        if call.data == 'support_pattern':
            text += 'с получением шаблонов расходов\n'
        if call.data == 'support_fill':
            text += 'с заполнением или загрузкой расходов\n'
        if call.data == 'support_pnl':
            text += 'с получением отчетов\n'
        if call.data == 'support_sub':
            text += 'с оплатой подписки\n'
        if call.data == 'support_work':
            text += 'с работой бота\n'
        if call.data == 'support_manager':
            text += 'требующие консультации с менеджером\n'
        await bot.send_message(ADMINS_ID[0], text)
        await call.message.answer('Спасибо за помощь!\n\nЯ уже сообщил менеджеру, он свяжется с тобой в ближайшее время.')


    # @dp.message_handler(commands=['help'], state='*')
    # async def send_help(message: types.Message, state):
    #     await message.answer('Напишите /cancel чтобы отменить действие', reply_markup=kb_markup_start)

    @dp.message_handler(commands=['users'], state='*')
    async def get_all_users(message: types.Message, state: FSMContext):
        if message.chat.id not in ADMINS_ID:
            return
        answer = await make_request(
            url='/admin/users',
            params={'chat_id': message.chat.id},
            method='get'
        )
        answer_text = '\n'.join([f"@{user['username']}: {user['created_at']}, подписка до: {user['subscribe_exp']}" for user in answer['users']])
        for i in range(0, len(answer_text), 4096):
            await message.answer(answer_text[i:i+4096])


    # @dp.message_handler(commands=['reg'], state='*')
    # async def registration_user(message: types.Message, state):
    #     await message.answer(f'Твой `chat_id`: {message.chat.id}', parse_mode=types.message.ParseMode.MARKDOWN)


    @dp.message_handler(commands=['full'], state='*')
    async def get_full_unit_economy(message: types.Message, state: FSMContext):
        if message.chat.id not in ADMINS_ID:
            return
        await message.answer('Введите стартовую дату, конечную дату и chat_id пользователя через пробел, по которым необходимо сформировать полную юнит экономику')
        await state.set_state(GenerateFullUnitEconomy.write_staff_data.state)

    @dp.message_handler(state=GenerateFullUnitEconomy.write_staff_data)
    async def write_staff_data_to_generate_full_unit_economy(message: types.Message, state: FSMContext):
        start_date, finish_date, user_chat_id = message.text.split(' ')
        try:
            start_date = datetime.strptime(start_date, "%d.%m.%Y").date()
            finish_date = datetime.strptime(finish_date, "%d.%m.%Y").date()
        except ValueError as e:
            await message.answer('Вы ввели неправильную дату, пожалуйста введите её в формате дд.мм.гггг')
            return
        print(start_date, finish_date, user_chat_id)

        data = await make_request(
            url='/unit-economy/full',
            params={'chat_id': message.chat.id},
            json_data={
                'start_date': start_date.strftime('%Y-%m-%d'),
                'finish_date': finish_date.strftime('%Y-%m-%d'),
                'user_chat_id': user_chat_id,
            }
        )
        if data:
            print(data)
            await message.answer('Время ожидания полной Юнит экономики не более 4 минут, ожидайте')
        else:
            await message.answer('Упс, что-то пошло не так')
        await state.finish()


    # @dp.message_handler(lambda c: c.text == 'Проверить подписку', state='*')
    # async def check_subscribe_status(message: types.Message, state: FSMContext):
    #     await message.answer('Выберите, что хотите сделать', reply_markup=kb_markup_subscribe)


    @dp.message_handler(commands=['subscription'], state='*')
    async def subscribe_status(message: types.Message, state):
        await state.finish()
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
                await message.answer('Сейчас у тебя действует Базовый тариф, по которому доступны:\n' \
                                     '✅ Анализ до 2-х брендов;\n' \
                                     '✅ Возможность анализа отчетов в скользящем окне 3-х месяцев.\n\n' \
                                     'Стоимость тарифа — 1990р / мес.')
            else:
                await message.answer('Сейчас у тебя нет действующих подписок', reply_markup=kb_markup_subscribe)
        else:
            await message.answer('Сейчас у тебя нет действующих подписок', reply_markup=kb_markup_subscribe)


    @dp.message_handler(lambda c: c.text == 'Оплатить подписку', state='*')
    async def send_keyboard_with_tariffs(message: types.Message, state: FSMContext):
        await message.answer('Выберите тариф, который хотите оплатить', reply_markup=kb_markup_subscribe_tariff)


    @dp.callback_query_handler(lambda c: c.data in PRICE_IDS, state='*')
    @keyboard_work
    async def subscribe_payment(call: types.CallbackQuery, state):
        """Метод, который отправляет счет пользователю"""
        if os.environ.get('PAYMENT_TOKEN').split(':')[1] == 'TEST':
            await bot.send_message(call.message.chat.id, 'Это тестовый вариант оплаты, так что нужно использовать тестовую карту с реквизитами 1111 1111 1111 1026')
        price = int(PRICES[call.data].amount)
        await bot.send_invoice(
            call.message.chat.id,
            title='Подписка на бота',
            description='Вы оплачиваете подписку на месяц на пользование ботом для составления отчетов по продажам WB',
            provider_token=os.environ.get('PAYMENT_TOKEN'),
            currency='rub',
            is_flexible=False,
            prices=[PRICES[call.data]],
            start_parameter='service-subscription',
            payload=f'subscription-for-user_{call.message.chat.id}',
            need_email=True,
            need_phone_number=True,
            send_email_to_provider=True,
            send_phone_number_to_provider=True,
            provider_data={
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

    @dp.pre_checkout_query_handler(lambda query: True)
    async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
        """Метод, который занимается проверкой правильности заполнения счета пользователем"""
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    @dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
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
            await message.answer(f'Произошла ошибка, пожалуйста, свяжитесь с поддержкой, указав следующие данные: {chat_id} и {message.successful_payment.provider_payment_charge_id}')
            return
        tariff_name = 'Базовый' # надо брать из списка по стоимости, как и возможности по тарифу
        tariff_scopes = '✅ Анализ до 2-х брендов;\n✅ Возможность анализа отчетов в скользящем окне 3-х месяцев.'
        text = f'Поздравляю с оформлением тарифа {tariff_name}!\nНапоминаю, что тебе доступно:\n{tariff_scopes}'
        await message.answer(text)
        return await message.answer('Ну что, приступим к работе? Выбери дальнейшее действие')


    # @dp.message_handler(lambda c: c.text == 'Проблемы с платежём', state='*')
    # async def subscribe_payment(message: types.Message, state):
    #     await message.answer('Отправь чек в виде файла')
    #     await state.set_state(DownloadСheque.download_cheque)

    # @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=DownloadСheque.download_cheque)
    # async def download_cheque(message: types.Message, state: FSMContext):
    #     await bot.send_message(ADMINS_ID[1], f'Проблемы с платежем у пользователя {message.chat.first_name}\nНикнейм пользователя: @{message.chat.username} #платёжка')  # TODO: Отправлять ник человека в ТГ
    #     await bot.send_document(chat_id=ADMINS_ID[1], document=message.document.file_id)  # Отправка сообщения админу с чеком
    #     await message.answer('Информация передана администратору и ожидает проверки', reply_markup=kb_markup_subscribe)


    @dp.message_handler(state=Questions.extra_report, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=Questions.extra_report)
    @check_state_exist
    async def cancel_download_extra_report_state(message: types.Message, state: FSMContext, current_state):
        user_info = await make_request(
            url='/downloads',
            params={'chat_id': message.chat.id},
            method='get'
        )
        await state.finish()
        if user_info['is_first_time']:
            return await message.answer('Отправь файл детализации')
        return await message.answer('Выбери, что ты хочешь сделать?')

    @dp.message_handler(state=WriteTaxRate.send_tax, commands=["cancel"])
    @dp.message_handler(state=WbDetailsState.download_wb_details, commands=["cancel"])
    @dp.message_handler(state=Questions.costs_change, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=WriteTaxRate.send_tax)
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=WbDetailsState.download_wb_details)
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=Questions.costs_change)
    @check_state_exist
    async def cancel_send_tax_rate_state(message: types.Message, state: FSMContext, current_state):
        await state.set_state(Questions.extra_report.state)
        return await message.answer('У тебя есть второй файл детализации из личного кабинета за этот же период? ' \
                                    'Если да, загрузи этот файл в бот', reply_markup=kb_download_extra_report)

    @dp.message_handler(state=DownloadFirstTime.download_other_information, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=DownloadFirstTime.download_other_information)
    @check_state_exist
    async def cancel_smth(message: types.Message, state: FSMContext, current_state):
        user_info = await make_request(
            url='/downloads',
            params={'chat_id': message.chat.id},
            method='get'
        )
        info = await state.get_data()
        if current_state == 'costs_pattern':
            if info.get('count_of_unloaded'):
                await message.answer(f"Не заполнена себестоимость {info['count_of_unloaded']} товаров. Хочешь их заполнить?", reply_markup=kb_markup_new_costs)
                await state.set_state(Questions.costs)
                return
            if user_info['is_first_time']:
                await state.set_state(WriteTaxRate.send_tax.state)
                return await message.answer('Напиши ставку налогообложения (числом без букв и символов). Например: 7')
            await state.finish()
            await state.set_state(Questions.extra_report.state)
            return await message.answer('У тебя есть второй файл детализации из личного кабинета? Если да, загрузи этот файл в бот', reply_markup=kb_download_extra_report)
        elif current_state == 'advertisements_pattern':
            await state.set_state(Questions.advertisements.state)
            return await message.answer('Были ли в этом периоде запуски *рекламы*?', reply_markup=kb_markup_download_ads, parse_mode=types.message.ParseMode.MARKDOWN)
        elif current_state == 'other_expenses_pattern':
            await state.set_state(Questions.other_expenses.state)
            return await message.answer('А как насчет *прочих расходов*: были ли расходы на платную приемку WB, платное хранение WB, расходы на офис и другие?', reply_markup=kb_markup_download_other_expenses, parse_mode=types.message.ParseMode.MARKDOWN)
        elif current_state == 'selfs_pattern':
            await state.set_state(Questions.selfs.state)
            return await message.answer('И последний вопрос — были ли в этом периоде *самовыкупы*? (Их я тоже учитываю в аналитике)', reply_markup=kb_markup_download_selfs, parse_mode=types.message.ParseMode.MARKDOWN)

    @dp.message_handler(state=Questions.advertisements, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=Questions.advertisements)
    @check_state_exist
    async def cancel_download_advertisements_state(message: types.Message, state: FSMContext, current_state):
        user_info = await make_request(
            url='/downloads',
            params={'chat_id': message.chat.id},
            method='get'
        )
        if user_info['is_first_time']:
            await state.set_state(DownloadFirstTime.download_other_information.state)
            await message.answer('Теперь нужно внести информацию по *себестоимости* товаров. Я отправлю тебе шаблон (с инструкцией), скачай его, внеси данные и загрузи файл в бот', parse_mode=types.message.ParseMode.MARKDOWN)
            await state.set_state(DownloadFirstTime.download_other_information.state)
            make_costs_file = await make_request(
                url='/patterns/costs',
                params={'chat_id': message.chat.id},
                method='get',
            )
        else:
            items_without_costs = await make_request(
                url='/patterns/costs/need-to-update',
                params={'chat_id': message.chat.id},
                method='get'
            )
            if len(items_without_costs['items']) > 0:
                answer_text = 'Супер! Я обнаружил в детализации *новые товары*, по которым не заполнена себестоимость. ' \
                            'Я уже добавил эти товары в таблицу, тебе осталось только заполнить себестоимость и отправить файл боту.'
                await message.answer(answer_text, parse_mode=types.message.ParseMode.MARKDOWN)
                await state.set_state(DownloadFirstTime.download_other_information.state)
                make_costs_file = await make_request(
                    url='/patterns/costs',
                    params={'chat_id': message.chat.id},
                    method='get',
                )
                return
            answer_text = "Супер! Изменились ли себестоимости товаров с прошлой недели? Измени сумму в столбце 'Закупочная цена', " \
                            "*если себестоимость изменилась*, и затем отправь файл боту."
            await message.answer(answer_text, reply_markup=kb_change_cost_price, parse_mode=types.message.ParseMode.MARKDOWN)
            await state.set_state(Questions.costs_change.state)
            return


    @dp.message_handler(state=Questions.other_expenses, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=Questions.other_expenses)
    @check_state_exist
    async def cancel_download_other_expenses_state(message: types.Message, state: FSMContext, current_state):
        await state.set_state(Questions.advertisements.state)
        return await message.answer('Были ли в этом периоде запуски *рекламы*?', reply_markup=kb_markup_download_ads, parse_mode=types.message.ParseMode.MARKDOWN)

    @dp.message_handler(state=Questions.selfs, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=Questions.selfs)
    @check_state_exist
    async def cancel_download_selfs_state(message: types.Message, state: FSMContext, current_state):
        await state.set_state(Questions.other_expenses.state)
        return await message.answer('А как насчет *прочих расходов*: были ли расходы на платную приемку WB, платное хранение WB, расходы на офис и другие?', reply_markup=kb_markup_download_other_expenses, parse_mode=types.message.ParseMode.MARKDOWN)

    @dp.message_handler(state=Questions.finish, commands=["cancel"])
    @dp.message_handler(lambda c: c.text.lower() == 'отменить последнее действие', state=Questions.finish)
    @check_state_exist
    async def cancel_finish_state(message: types.Message, state: FSMContext, current_state):
        await state.set_state(Questions.selfs.state)
        return await message.answer('И последний вопрос — были ли в этом периоде *самовыкупы*? (Их я тоже учитываю в аналитике)', reply_markup=kb_markup_download_selfs, parse_mode=types.message.ParseMode.MARKDOWN)


    # @dp.message_handler(lambda c: c.text == 'Продолжить', state='*')
    # async def move_to_reports_keyboard(message: types.Message, state: FSMContext):
    #     answer = await make_request(
    #         url='/users',
    #         params={'chat_id': message.chat.id},
    #         method='get'
    #     )
    #     print(answer)
    #     if not answer['success'] or not answer['active']:
    #         await message.answer('Для начала оплатите подписку', reply_markup=kb_markup_subscribe)
    #         return
    #     await message.answer('Что вы хотите рассчитать?', reply_markup=kb_markup_start)


    # @dp.message_handler(lambda c: c.text == 'ОПиУ', state='*')
    # async def opi_FAQ(message: types.Message, state):
    #     if message.chat.id not in ADMINS_ID:
    #         await message.answer('Раздел в разработке')
    #         return
    #     answer = "Для корректного рассчёта P&L Вам надо загрузить:\n" \
    #         "*Обязательно:*\n" \
    #         "1. Детализации за неделю в xlsx файле с уникальными названиями\n" \
    #         "2. Себестоимости [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1pBr_D_3ZJXRRo7jCclMHmu0Snf_cSk3I/edit?usp=sharing&ouid=118028734681847247789&rtpof=true&sd=true)\n" \
    #         "*По желанию:*\n" \
    #         "3. Самовыкупы [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1gwR-IW3xJy4Q9m9kSjwFiaipqusirdHp/edit?usp=sharing&ouid=118028734681847247789&rtpof=true&sd=true)\n" \
    #         "4. Прочие расходы [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1HMT3wTMAm6pHIeqDTFxWlq4pvXCvRw0d/edit?usp=sharing&ouid=118028734681847247789&rtpof=true&sd=true)\n" \
    #         "5. Расходы на рекламу [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1NjxVyVFyp0erJ9f1tSFdVjd07kz6QSo9kSKO7qe_YlA/edit#gid=0)\n"
    #     await message.answer(answer, parse_mode=types.message.ParseMode.MARKDOWN, reply_markup=types.ReplyKeyboardRemove(), disable_web_page_preview=True)
    #     await message.answer('После подготовки всех файлов жми Готово', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('Готово', callback_data='opi_ready')))

    # @dp.message_handler(lambda c: c.text == 'Юнит-экономика', state='*')
    # async def unit_economy_FAQ(message: types.Message, state):
    #     answer = "Для этого вам нужно загрузить:\n" \
    #         "*Обязательно:*\n" \
    #         "1. Детализации за неделю в xlsx файле с уникальными названиями\n" \
    #         "2. Себестоимости [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1pBr_D_3ZJXRRo7jCclMHmu0Snf_cSk3I/edit?usp=sharing&ouid=118028734681847247789&rtpof=true&sd=true)\n" \
    #         "*По желанию:*\n" \
    #         "3. Самовыкупы [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1gwR-IW3xJy4Q9m9kSjwFiaipqusirdHp/edit?usp=sharing&ouid=118028734681847247789&rtpof=true&sd=true)\n" \
    #         "4. Расходы на рекламу [Ссылка на шаблон](https://docs.google.com/spreadsheets/d/1NjxVyVFyp0erJ9f1tSFdVjd07kz6QSo9kSKO7qe_YlA/edit#gid=0)\n"
    #     await message.answer(answer, parse_mode=types.message.ParseMode.MARKDOWN, reply_markup=types.ReplyKeyboardRemove(), disable_web_page_preview=True)
    #     await message.answer('После подготовки всех файлов жмите Готово', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('Готово', callback_data='unit_ready')))

    # @dp.callback_query_handler(lambda c: c.data == 'opi_ready', state='*')
    # @keyboard_work
    # async def download_files_to_opi(call: types.CallbackQuery, state):
    #     await call.message.answer('Загрузить', reply_markup=kb_markup_download_opi)

    # @dp.callback_query_handler(lambda c: c.data == 'unit_ready', state='*')
    # @keyboard_work
    # async def download_files_to_unit_economy(call: types.CallbackQuery, state):
    #     await call.message.answer('Загрузить', reply_markup=kb_markup_download_unit)


    # @dp.callback_query_handler(lambda c: c.data in ('report_unit', 'report_opi'), state='*')
    # @keyboard_work
    # async def download_wb_report(call: types.CallbackQuery, state: FSMContext):
    #     await call.message.answer('Отправте файл с Детализацией WB или если хотите отменить, /cancel')
    #     await state.set_state(WbDetailsState.download_wb_details.state)
    #     await state.update_data(callback_data=call.data)

    @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=WbDetailsState.download_wb_details)
    @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=Questions.extra_report)
    async def get_wb_details_file(message: types.Message, state: FSMContext):
        await message.answer('Идет загрузка детализации', reply_markup=kb_back)
        file_in_io = io.BytesIO()
        await message.document.download(destination_file=file_in_io)
        file_in_io.name = message.document.file_name

        answer = await make_request(
            url='/reports',
            params={'chat_id': message.chat.id},
            files={
                'file': file_in_io
            },
        )
        user_info = await make_request(
            url='/downloads',
            params={'chat_id': message.chat.id},
            method='get',
        )
        if not answer:
            await message.answer('Произошла ошибка, пожалуйста, свяжитесь с технической поддержкой')
            return
        if answer['success']:
            await state.update_data(compute_items_without_costs=1)
            if user_info['is_first_time']:
                if user_info['wb_detail_count'] < 2:
                    res = await make_request(
                        url='/back/current',
                        params={'chat_id': message.chat.id},
                        json_data={'state': 'first'}
                    )
                    print(res)
                    await message.answer('Детализация загружена. У тебя есть второй файл детализации (отчет по СНГ) из личного кабинета? ' \
                                            'Если да, загрузи этот файл в бот', reply_markup=kb_download_extra_report)
                    await state.set_state(Questions.extra_report.state)
                    return
                answer_text = "Напиши ставку налогообложения (числом без букв и символов). Например: 7"
                await state.set_state(WriteTaxRate.send_tax.state)
                await message.answer(answer_text)
                return
            else:
                current_state = await state.get_data()
                if not current_state.get('downloaded_once'):
                    res = await make_request(
                        url='/back/current',
                        params={'chat_id': message.chat.id},
                        json_data={'state': 'first'}
                    )
                    print(res)
                    await message.answer('Детализация загружена. У тебя есть второй файл детализации (отчет по СНГ) из личного кабинета? ' \
                                        'Если да, загрузи этот файл в бот', reply_markup=kb_download_extra_report)
                    await state.set_state(Questions.extra_report.state)
                    await state.update_data(downloaded_once=True)
                    print(state)
                    return
                items_without_costs = await make_request(
                    url='/patterns/costs/need-to-update',
                    params={'chat_id': message.chat.id},
                    method='get'
                )
                if len(items_without_costs['items']) > 0:
                    answer_text = 'Супер! Я обнаружил в детализации *новые товары*, по которым не заполнена себестоимость. ' \
                                'Я уже добавил эти товары в таблицу, тебе осталось только заполнить себестоимость и отправить файл боту.'
                    await message.answer(answer_text, parse_mode=types.message.ParseMode.MARKDOWN)
                    await state.set_state(DownloadFirstTime.download_other_information.state)
                    make_costs_file = await make_request(
                        url='/patterns/costs',
                        params={'chat_id': message.chat.id},
                        method='get',
                    )
                    return
                answer_text = "Супер! Изменились ли себестоимости товаров с прошлой недели? Измени сумму в столбце 'Закупочная цена', " \
                                "*если себестоимость изменилась*, и затем отправь файл боту."
                await message.answer(answer_text, reply_markup=kb_change_cost_price, parse_mode=types.message.ParseMode.MARKDOWN)
                await state.set_state(Questions.costs_change.state)
                return
        else:
            kb = ''
            if 'type' in answer:
                if answer['type'] == 'lifetime':
                    kb = kb_lifetime_error
                if answer['type'] == 'count':
                    kb = kb_brand_count_error
            await message.answer(answer['error'], reply_markup=kb)
            return


    @dp.callback_query_handler(lambda c: c.data in ('costs_yes', 'costs_no'), state=Questions.costs_change)
    @keyboard_work
    async def download_new_costs(call: types.CallbackQuery, state: FSMContext):
        if call.data == 'costs_no':
            answer_text = 'Отлично! Были ли в этом периоде запуски рекламы?'
            await state.set_state(Questions.advertisements.state)
            return await call.message.answer(answer_text, reply_markup=kb_markup_download_ads)
        make_costs_file = await make_request(
            url='/patterns/costs',
            params={'chat_id': call.message.chat.id},
            method='get',
        )
        await state.set_state(DownloadFirstTime.download_other_information.state)


    @dp.message_handler(state=WriteTaxRate.send_tax)
    async def set_user_tax_rate(message: types.Message, state: FSMContext):
        tax_rate = message.text
        try:
            tax_rate = int(tax_rate)
        except ValueError:
            return await message.answer('Ты ввел некорректную налоговую ставку, пожалуйста введи её числом, например 7')
        answer = await make_request(
            url='/users/tax',
            params={'chat_id': message.chat.id},
            json_data={'tax_rate': tax_rate}
        )
        if not answer['success']:
            return await message.answer('Ты ввёл некорректную налоговую ставку, введи правильную')

        answer_text = "Круто! Теперь нужно внести информацию по *себестоимости* товаров. " \
                        "Я отправлю тебе шаблон (с инструкцией), скачай его, внеси данные и загрузи файл в бот"
        ms = await message.answer(answer_text, parse_mode=types.message.ParseMode.MARKDOWN)
        await state.set_state(DownloadFirstTime.download_other_information.state)
        make_costs_file = await make_request(
            url='/patterns/costs',
            params={'chat_id': message.chat.id},
            method='get',
        )


    @dp.callback_query_handler(lambda c: c.data == 'extra_repo_no', state=Questions.extra_report)
    @keyboard_work
    async def check_to_download_extra_report(call: types.CallbackQuery, state: FSMContext):
        current_state = await state.get_data()
        if not current_state.get('downloaded_once'):
            answer_text = "Напиши ставку налогообложения (числом без букв и символов). Например: 7"
            await state.set_state(WriteTaxRate.send_tax.state)
            await call.message.answer(answer_text)
            return

        items_without_costs = await make_request(
            url='/patterns/costs/need-to-update',
            params={'chat_id': call.message.chat.id},
            method='get'
        )
        if len(items_without_costs['items']) > 0:
            answer_text = 'Супер! Я обнаружил в детализации новые товары, по которым не заполнена себестоимость. ' \
                        'Я уже добавил эти товары в таблицу, тебе осталось только заполнить себестоимость и отправить файл боту.'
            await call.message.answer(answer_text)
            await state.set_state(DownloadFirstTime.download_other_information.state)
            make_costs_file = await make_request(
                url='/patterns/costs',
                params={'chat_id': call.message.chat.id},
                method='get',
            )
            return

        answer_text = "Супер! Изменились ли себестоимости товаров с прошлой недели? Измени сумму в столбце 'Закупочная цена', " \
                        "если себестоимость изменилась, и затем отправь файл боту."
        await call.message.answer(answer_text, reply_markup=kb_change_cost_price)
        await state.set_state(Questions.costs_change.state)
        return


    @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=DownloadFirstTime.download_other_information)
    async def download_other_information(message: types.Message, state: FSMContext):
        file_in_io = io.BytesIO()
        await message.document.download(destination_file=file_in_io)
        file_in_io.name = message.document.file_name

        answer = await make_request(
            url='/files/download',
            params={'chat_id': message.chat.id},
            files={
                'file': file_in_io
            }
        )
        print(answer)
        if not answer:
            await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой')
            return
        if not answer['success']:
            kb = ''
            if 'type' in answer:
                if answer['type'] == 'lifetime':
                    kb = kb_lifetime_error
                if answer['type'] == 'count':
                    kb = kb_brand_count_error
            await message.answer(answer['error'], reply_markup=kb)
            return

        key = answer['downloaded']
        if key == 'selfs':
            await state.finish()
            answer = await make_request(
                url='/reports/get',
                params={'chat_id': message.chat.id},
            )
            print(answer['success'])
            if answer['success']:
                await message.answer('Лови два отчета: ОПиУ и Юнит-экономику!🔥')
            return
        if key == 'others':
            await message.answer('Прочие расходы загружены!\n' \
                                    'И последний вопрос — были ли в этом периоде *самовыкупы*? (Их я тоже учитываю в аналитике)', 
                                    reply_markup=kb_markup_download_selfs, parse_mode=types.message.ParseMode.MARKDOWN)
            await state.set_state(Questions.selfs.state)
        if key == 'ads':
            await message.answer('Рекламные расходы загружены!\n' \
                                    'Теперь отчет будет более точным')
            await message.answer('А как насчет *прочих расходов*: были ли расходы на платную приемку WB, платное хранение WB, расходы на офис и другие?',
                                    reply_markup=kb_markup_download_other_expenses, parse_mode=types.message.ParseMode.MARKDOWN)
            await state.set_state(Questions.other_expenses.state)
        if key == 'costs':
            items_without_cost_price = await make_request(
                url='/patterns/costs/need-to-update',
                params={'chat_id': message.chat.id},
                method='get'
            )
            length = len(items_without_cost_price['items'])
            if length > 0:
                await message.answer(
                    f'Не заполнена *себестоимость* {length} товаров.\nХочешь её заполнить?',
                    reply_markup=kb_markup_new_costs,
                    parse_mode=types.message.ParseMode.MARKDOWN
                )
                await state.set_state(Questions.costs.state)
                await state.update_data(count_of_unloaded=length)
                return
            await state.update_data(compute_items_without_costs=1)
            await message.answer(
                'Отлично! Были ли в этом периоде *запуски рекламы*?',
                reply_markup=kb_markup_download_ads,
                parse_mode=types.message.ParseMode.MARKDOWN
            )
            await state.set_state(Questions.advertisements.state)
        return

    @dp.callback_query_handler(lambda c: c.data in ('new_costs_yes', 'new_costs_no'), state=Questions.costs)
    @keyboard_work
    async def items_without_costs_download_handler(call: types.CallbackQuery, state: FSMContext):
        info = await state.get_data()
        if call.data == 'new_costs_no':
            await call.message.answer('Так как заполнена себестоимость не всех товаров, отчеты могут быть некорректные. Выбери, как считать эти товары в отчетах', reply_markup=kb_markup_items_without_costs)
            return await state.set_state(Questions.items_without_costs.state)
        await state.set_state(DownloadFirstTime.download_other_information.state)
        await call.message.answer(f"Отправляю файл себестоимости, тебе осталось внести данные по {info['count_of_unloaded']} товарам")
        make_costs_file = await make_request(
            url='/patterns/costs',
            params={'chat_id': call.message.chat.id},
            method='get',
        )
        return

    @dp.callback_query_handler(lambda c: c.data in ('without_no', 'without_yes', 'without_rewrite'), state=Questions.items_without_costs)
    @keyboard_work
    async def choose_reports_computing(call: types.CallbackQuery, state: FSMContext):
        if call.data == 'without_rewrite':
            info = await state.get_data()
            await state.set_state(DownloadFirstTime.download_other_information.state)
            await call.message.answer(f"Отправляю файл себестоимости, тебе осталось внести данные по {info['count_of_unloaded']} товарам")
            make_costs_file = await make_request(
                url='/patterns/costs',
                params={'chat_id': call.message.chat.id},
                method='get',
            )
            return
        compute_items_without_costs = 1 if call.data == 'without_yes' else 0
        if compute_items_without_costs == 1:
            text = 'Товары без себестоимости будут считаться с *нулевой себестоимостью*.'
        else:
            text = 'Товары без себестомиости *не будут* учитываться в отчетах.'
        await state.update_data(compute_items_without_costs=compute_items_without_costs)
        await call.message.answer(text, parse_mode=types.message.ParseMode.MARKDOWN)
        await call.message.answer('Отлично! Были ли в этом периоде *запуски рекламы*?', reply_markup=kb_markup_download_ads, parse_mode=types.message.ParseMode.MARKDOWN)
        return await state.set_state(Questions.advertisements.state)

    @dp.callback_query_handler(lambda c: c.data in ('ads_no', 'ads_yes'), state=Questions.advertisements)
    @keyboard_work
    async def ads_download_handler(call: types.CallbackQuery, state: FSMContext):
        if call.data == 'ads_no':
            await state.set_state(Questions.other_expenses.state)
            return await call.message.answer('А как насчет *прочих расходов*: были ли расходы на платную приемку WB, платное хранение WB, расходы на офис и другие?',
                                                reply_markup=kb_markup_download_other_expenses, parse_mode=types.message.ParseMode.MARKDOWN)
        await call.message.answer('Держи шаблон для заполнения *рекламных расходов* — заполни его и загрузи в бот', parse_mode=types.message.ParseMode.MARKDOWN)
        make_ads_file = await make_request(
            url='/patterns/ads',
            params={'chat_id': call.message.chat.id},
            method='get',
        )
        await state.set_state(DownloadFirstTime.download_other_information.state)


    @dp.callback_query_handler(lambda c: c.data in ('exp_no', 'exp_yes'), state=Questions.other_expenses)
    @keyboard_work
    async def other_expenses_download_handler(call: types.CallbackQuery, state: FSMContext):
        if call.data == 'exp_no':
            await state.set_state(Questions.selfs.state)
            return await call.message.answer('Круто, что удалось обойтись без дополнительных трат!\n' \
                                                'И последний вопрос — были в этом периоде *самовыкупы*? (Их я тоже учитываю в аналитике)',
                                                reply_markup=kb_markup_download_selfs, parse_mode=types.message.ParseMode.MARKDOWN)
        await call.message.answer('Шаблон с дополнительными тратами')
        make_other_expenses_file = await make_request(
            url='/patterns/other-expenses',
            params={'chat_id': call.message.chat.id},
            method='get',
        )
        await state.set_state(DownloadFirstTime.download_other_information.state)


    @dp.callback_query_handler(lambda c: c.data in ('selfs_no', 'selfs_yes'), state=Questions.selfs)
    @keyboard_work
    async def selfs_download_handler(call: types.CallbackQuery, state: FSMContext):
        if call.data == 'selfs_no':
            current_state = await state.get_data()
            await state.finish()
            answer = await make_request(
                url='/reports/get',
                params={'chat_id': call.message.chat.id, 'item_without_costs': current_state.get('compute_items_without_costs', 1)},
            )
            print(answer['success'])
            if answer['success']:
                await call.message.answer('Лови два отчета: ОПиУ и Юнит-экономику!🔥')
            return
        await call.message.answer('Шаблон с самовыкупами')
        make_selfs_file = await make_request(
            url='/patterns/selfs',
            params={'chat_id': call.message.chat.id},
            method='get',
        )
        await state.set_state(DownloadFirstTime.download_other_information.state)


    # @dp.callback_query_handler(lambda c: c.data in ('self_unit', 'self_opi'), state='*')
    # @keyboard_work
    # async def download_self_payments(call: types.CallbackQuery, state: FSMContext):
    #     await call.message.answer('Отправте файл с самовыкупами из MPBoost или если хотите отменить, /cancel')
    #     await state.set_state(SelfPayments.download_self_payments.state)
    #     await state.update_data(callback_data=call.data)

    # @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=SelfPayments.download_self_payments)
    # async def get_self_payments_file(message: types.Message, state: FSMContext):
    #     await message.answer('Отчет с самовыкупами получен, ожидайте загрузки, не более 4 минут')
    #     current_state = await state.get_data()
    #     file_in_io = io.BytesIO()
    #     await message.document.download(destination_file=file_in_io)
    #     file_in_io.name = message.document.file_name

    #     answer = await make_request(
    #         url='/self-payments',
    #         params={'chat_id': message.chat.id},
    #         files={
    #             'file': file_in_io
    #         },
    #     )
    #     print(answer)
    #     if not answer:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #         return
    #     if answer['success']:
    #         await message.answer('Самовыкупы загружены, подождите пока они сопостявятся с детализацией, не более 4 минут')
    #         new_res = await make_request(
    #             url='/self-payments/match',
    #             params={'chat_id': message.chat.id},
    #         )
    #     else:
    #         await message.answer(f"Произошла ошибка:\n{answer['error']}")
    #         return

    #     if not new_res:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #         return

    #     if new_res['success']:
    #         await message.answer('Успешно начато сопоставление выкупов с детализацией, ожидайте завершения')

    #     await message.answer('Загрузить', reply_markup=kb_markup_download_unit if current_state['callback_data'] == 'self_unit' else kb_markup_download_opi)
    #     await state.finish()


    # @dp.callback_query_handler(lambda c: c.data in ('costs_unit', 'costs_opi'), state='*')
    # @keyboard_work
    # async def download_cost_prices(call: types.CallbackQuery, state: FSMContext):
    #     await call.message.answer('Отправте файл с себестоимостями товаров или если хотите отменить, /cancel')
    #     await state.set_state(CostPrices.download_cost_price.state)
    #     await state.update_data(callback_data=call.data)

    # @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=CostPrices.download_cost_price)
    # async def get_cost_price_file(message: types.Message, state: FSMContext):
    #     await message.answer('Файл с себестомостями получен, ожидайте загрузки, не более 4 минут')
    #     current_state = await state.get_data()
    #     file_in_io = io.BytesIO()
    #     await message.document.download(destination_file=file_in_io)
    #     file_in_io.name = message.document.file_name
    #     res = await make_request(
    #         url='/costs',
    #         params={'chat_id': message.chat.id},
    #         files={
    #             'file': file_in_io
    #         },
    #     )
    #     if not res:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #         return
    #     if res['success']:
    #         await message.answer('Себестоимости успешно загружены')

    #     await message.answer('Загрузить', reply_markup=kb_markup_download_unit if current_state['callback_data'] == 'costs_unit' else kb_markup_download_opi)
    #     await state.finish()


    # @dp.callback_query_handler(lambda c: c.data in ('ads_unit', 'ads_opi'), state='*')
    # @keyboard_work
    # async def download_advertisement(call: types.CallbackQuery, state: FSMContext):
    #     await call.message.answer('Отправте файл с расходами на рекламу или если хотите отменить, /cancel')
    #     await state.set_state(Advertisement.download_advertisement.state)
    #     await state.update_data(callback_data=call.data)

    # @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=Advertisement.download_advertisement)
    # async def get_advertisement_file(message: types.Message, state: FSMContext):
    #     await message.answer('Файл с расходами на рекламу получен, ожидайте загрузки, не более 4 минут')
    #     current_state = await state.get_data()
    #     file_in_io = io.BytesIO()
    #     await message.document.download(destination_file=file_in_io)
    #     file_in_io.name = message.document.file_name
    #     res = await make_request(
    #         url='/ads',
    #         params={'chat_id': message.chat.id},
    #         files={
    #             'file': file_in_io
    #         }
    #     )
    #     if not res:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #         return
    #     if res['success']:
    #         await message.answer('Расходы на рекламу успешно загружены')

    #     await message.answer('Загрузить', reply_markup=kb_markup_download_unit if current_state['callback_data'] == 'ads_unit' else kb_markup_download_opi)
    #     await state.finish()


    # @dp.callback_query_handler(lambda c: c.data == 'other_opi')
    # @keyboard_work
    # async def download_other_information_file(call: types.CallbackQuery, state: FSMContext):
    #     await call.message.answer('Отправте файл с Прочими расходами или если хотите отменить, /cancel')
    #     await state.set_state(OtherInformation.download_other_information.state)

    # @dp.message_handler(content_types=types.ContentType.DOCUMENT, state=OtherInformation.download_other_information)
    # async def get_other_information_file(message: types.Message, state: FSMContext):
    #     await message.answer('Файл с Прочими расходами получен, ожидайте загрузки, не более 4 минут')
    #     file_in_io = io.BytesIO()
    #     await message.document.download(destination_file=file_in_io)
    #     file_in_io.name = message.document.file_name
    #     res = await make_request(
    #         url='/expenses',
    #         params={'chat_id': message.chat.id},
    #         files={
    #             'file': file_in_io
    #         },
    #     )
    #     if not res:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #         return
    #     if res['success']:
    #         await message.answer('Прочие расходы успешно загружены')
    #     await message.answer('Загрузить', reply_markup=kb_markup_download_opi)
    #     await state.finish()


    # @dp.callback_query_handler(lambda c: c.data == 'get_unit', state='*')
    # @keyboard_work
    # async def get_unit_economy(call: types.CallbackQuery, state):
    #     await call.message.answer('Введите начальную дату в формате дд.мм.гггг')
    #     await state.set_state(GetUnitEconomy.waiting_for_start_date.state)

    # @dp.message_handler(content_types=types.ContentTypes.ANY, state=GetUnitEconomy.waiting_for_start_date)
    # @check_date
    # async def set_start_date_to_get_unit_economy(message: types.Message, state: FSMContext, start_date):
    #     await state.update_data(start_date=start_date)
    #     await message.answer('Введите конечную дату в формате дд.мм.гггг')
    #     await state.set_state(GetUnitEconomy.waiting_for_finish_date)

    # @dp.message_handler(content_types=types.ContentTypes.ANY, state=GetUnitEconomy.waiting_for_finish_date)
    # @check_date
    # async def set_finish_date_and_get_unit_economy(message: types.Message, state: FSMContext, finish_date):
    #     date = await state.get_data()
    #     start_date = date['start_date']
    #     if start_date > finish_date:
    #         await message.answer('Конечная дата не может быть меньше начальной, введите конечную дату в формате дд.мм.гггг')
    #         return

    #     data = await make_request(
    #         '/unit-economy',
    #         {'chat_id': message.chat.id},
    #         {
    #             'start_date': datetime.strptime(start_date, "%d.%m.%Y").date().strftime('%Y-%m-%d'),
    #             'finish_date': datetime.strptime(finish_date, "%d.%m.%Y").date().strftime('%Y-%m-%d'),
    #         }
    #     )

    #     if data:
    #         await message.answer('Время ожидания Юнит-экономики не более 4 минут, ожидайте', reply_markup=kb_markup_start)
    #     else:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #     await state.finish()


    # @dp.callback_query_handler(lambda c: c.data == 'get_opi', state='*')
    # @keyboard_work
    # async def get_opi_report(call: types.CallbackQuery, state):
    #     await call.message.answer('Введите название бренда, по которому нужна P&L')
    #     await state.set_state(GetOPI.waiting_for_brand_name)

    # @dp.message_handler(content_types=types.ContentTypes.ANY, state=GetOPI.waiting_for_brand_name)
    # async def set_dates_to_get_opi_report(message: types.Message, state: FSMContext):
    #     print(message.text)
    #     await message.answer('Введите начальную дату в формате дд.мм.гггг')
    #     await state.set_state(GetOPI.waiting_for_start_date.state)
    #     await state.update_data(brand_name=message.text)

    # @dp.message_handler(content_types=types.ContentTypes.ANY, state=GetOPI.waiting_for_start_date)
    # @check_date
    # async def set_start_date_to_get_opi_report(message: types.Message, state: FSMContext, start_date):
    #     await state.update_data(start_date=start_date)
    #     await message.answer('Введите конечную дату в формате дд.мм.гггг')
    #     await state.set_state(GetOPI.waiting_for_finish_date)

    # @dp.message_handler(content_types=types.ContentTypes.ANY, state=GetOPI.waiting_for_finish_date)
    # @check_date
    # async def set_finish_date_and_get_opi_report(message: types.Message, state: FSMContext, finish_date):
    #     data = await state.get_data()
    #     start_date = data['start_date']
    #     if start_date > finish_date:
    #         await message.answer('Конечная дата не может быть меньше начальной, введите конечную дату в формате дд.мм.гггг')
    #         return

    #     data = await make_request(
    #         '/opi',
    #         {'chat_id': message.chat.id},
    #         {
    #             'start_date': datetime.strptime(start_date, "%d.%m.%Y").date().strftime('%Y-%m-%d'),
    #             'finish_date': datetime.strptime(finish_date, "%d.%m.%Y").date().strftime('%Y-%m-%d'),
    #             'brand_name': [data['brand_name']],
    #         }
    #     )

    #     if data:
    #         print(data)
    #         await message.answer('Время ожидания P&L не более 1 минуты, ожидайте', reply_markup=kb_markup_start)
    #     else:
    #         await message.answer('Произошла ошибка, пожалуйста, свяжитесь с поддержкой', reply_markup=kb_markup_start)
    #     await state.finish()


    @dp.message_handler(content_types=types.ContentTypes.ANY)
    async def start_bot_after_delay(message: types.Message, state: FSMContext):
        print(state)
        answer = await make_request(
            url='/downloads',
            params={'chat_id': message.chat.id},
            method='get',
        )
        is_file = bool(message.document)
        if not answer:
            return await message.answer('Напиши /report, чтобы сформировать отчет')
        if not answer['success']:
            return await message.answer('Ваша подписка просрочена', reply_markup=kb_markup_subscribe)
        if answer['is_first_time']:
            if not answer['seller_url']:
                return await download_seller_url(message, state)
            elif answer['wb_detail_count'] == 0 and is_file:
                await state.set_state(WbDetailsState.download_wb_details.state)
                return await get_wb_details_file(message, state)
            elif is_file:
                await state.update_data(compute_items_without_costs=1)
                await state.set_state(DownloadFirstTime.download_other_information.state)
                return await download_other_information(message, state)
            else:
                await message.answer('Напиши /report, чтобы сформировать отчет')
        else:
            if is_file:
                await state.set_state(WbDetailsState.download_wb_details.state)
                return await get_wb_details_file(message, state)
            await message.answer('Напиши /report, чтобы сформировать отчет')


    # @dp.message_handler(commands=["promo"], state="*")
    # async def send_promo_code(message: types.Message, state: FSMContext):
    #     await state.set_state(WritePromoCode.send_promo_code.state)
    #     return await message.answer('Введите ваш промокод')

    # @dp.message_handler(content_types=types.ContentType.TEXT)
    # async def check_promo_code_and_give_payload(message: types.Message, state: FSMContext):
    #     promo_code = message.text
    #     check_promo = await make_request(
    #         url='/promos/use',
    #         params={'chat_id': message.chat.id},
    #         json_data={
    #             'promo_code': promo_code
    #         }
    #     )
    #     if not check_promo['success']:
    #         await state.finish()
    #         return await message.answer('Этот промокод недействительный, начните сначала')
    #     if os.environ.get('PAYMENT_TOKEN').split(':')[1] == 'TEST':
    #         await bot.send_message(message.chat.id, 'Это тестовый вариант оплаты, так что нужно использовать тестовую карту с реквизитами 1111 1111 1111 1026')
    #     price = int(int(PRICES['1'].amount) / 2.02)
    #     await bot.send_invoice(
    #         message.chat.id,
    #         title='Подписка на бота',
    #         description='Вы оплачиваете подписку на месяц на пользование ботом для составления отчетов по продажам WB',
    #         provider_token=os.environ.get('PAYMENT_TOKEN'),
    #         currency='rub',
    #         is_flexible=False,
    #         prices=[PRICES['1']],
    #         start_parameter='service-subscription',
    #         payload=f'subscription-for-user_{message.chat.id}',
    #         need_email=True,
    #         need_phone_number=True,
    #         send_email_to_provider=True,
    #         send_phone_number_to_provider=True,
    #         provider_data={
    #             'receipt': {
    #                 'items': [
    #                     {
    #                         'description': 'оплата подписки market.top',
    #                         'quantity': '1.00',
    #                         'amount': {
    #                             'value': "{0:.2f}".format(price / 100),
    #                             'currency': 'RUB'
    #                         },
    #                         'vat_code': 1
    #                     }
    #                 ]
    #             }
    #         }
    #     )


    return await process_event(update, dp)
