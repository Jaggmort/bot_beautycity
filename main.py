import os

import dotenv
import asyncio
from bot_beautycity import funcs
from bot_beautycity import markups as m
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher.filters import Text
from asgiref.sync import sync_to_async
from pathlib import Path
from textwrap import dedent
from admin_beautycity.models import Client, Schedule, Service, Specialist
from phonenumber_field.phonenumber import PhoneNumber
from phonenumbers.phonenumberutil import NumberParseException
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup
from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram.types.message import ContentType
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
dotenv.load_dotenv(Path(BASE_DIR, '.env'))
token = os.environ['BOT_TOKEN']
PAYMENT_TOKEN = os.environ['PAYMENT_TOKEN']

bot = Bot(token=token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)


class UserState(StatesGroup):
    choice_service = State()
    choice_specialist = State()
    choice_datetime = State()
    get_registration = State()
    set_name_phone = State()
    phone_verification = State()

@dp.message_handler()
async def start_conversation(msg: types.Message, state: FSMContext):
    messages_responses = []
    message = dedent("  Welcome! \n"
                     "BeautyCity beauty salon is not only highly professional services, but also a cozy salon where "
                     "guests are always welcome. \nPerfection in work and creativity, attentive craftsmen will take "
                     "into account and realize all your wishes!")
    messages_responses.append(await msg.answer(dedent(message)))
    records_count = await sync_to_async(funcs.get_records_count)(msg.from_user.username)
    if records_count:
        message = await msg.answer(f'Welcome back, {msg.from_user.first_name}. '
                                   f'You already had recordings: {records_count}.')
    else:
        message = await msg.answer(f'Hello, {msg.from_user.first_name}.')
    messages_responses.append(message)
    await msg.answer('Main menu', reply_markup=m.client_start_markup)
    await state.update_data(messages_responses=messages_responses)


@dp.callback_query_handler(text="exit", state=[UserState, None])
async def exit_client_proceeding(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await cb.message.answer('Main menu', reply_markup=m.client_start_markup)
    await state.reset_state(with_data=False)
    await cb.answer()


@dp.callback_query_handler(text="call_to_us", state=[UserState, None])
async def call_to_us_message(cb: types.CallbackQuery):
    await cb.message.answer('We are glad to receive your call at any time – +7(800)555-35-35')
    await cb.answer()


@dp.callback_query_handler(Text('choice_service'), state=[UserState, None])
async def service_choosing(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    try:
        messages_responses = await state.get_data('messages_responses')
        for message in messages_responses['messages_responses']:
            await message.delete()
        await state.update_data(messages_responses=[])
    except TypeError:
        pass
    await cb.message.answer('Choosing a service:', reply_markup=m.get_service)
    await UserState.choice_service.set()
    await cb.answer()


@dp.callback_query_handler(Text([service for service in
                                 Service.objects.all().values_list('name_english', flat=True)]),
                           state=UserState.choice_service)
async def set_service(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await state.update_data(tg_id=cb.from_user.id)  # сохраняем tg_id кто кликнул

    async for service in Service.objects.filter(name_english=cb.data):  # результат - одно значение!
        await state.update_data(service_id=service.pk)
        await state.update_data(service_name=service.name)

    messages_responses = await state.get_data('messages_responses')
    messages_responses['messages_responses'].append(await cb.message.answer(f'Service "{service.name}" '
                                                                            f'costs {service.cost} rur.'))
    await cb.message.answer('Choosing a specialist:', reply_markup=m.get_specialist)
    await UserState.choice_specialist.set()


@dp.callback_query_handler(Text([specialist for specialist in
                                 Specialist.objects.all().values_list('name', flat=True)] + ['Any']),
                           state=UserState.choice_specialist)
async def set_specialist(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    payloads = await state.get_data()
    for message in payloads['messages_responses']:
        await message.delete()
    if cb.data == 'Any':
        await state.update_data(specialist_id=None)  # при выборе "Любой" ID специалиста None
        await state.update_data(specialist_name=None)

    else:
        async for specialist in Specialist.objects.filter(name=cb.data):  # результат - одно значение!
            await state.update_data(specialist_id=specialist.pk)
            await state.update_data(specialist_name=specialist.name)

        # ЗДЕСЬ НАДО ВСТАВИТЬ ВЫБОР ИЗ КАЛЕНДАРЯ!
        # И ЕСЛИ ВЫБРАН ЛЮБОЙ СПЕЦИАЛИСТ - ПОТОМ КОНКРЕТНОГО СОХРАНИТЬ В state

    # выбор ячейки приема по ИД специалиста - первой попавшейся свободной
    schedule = None
    async for schedule in Schedule.objects.filter(specialist=specialist.pk,
                                                  client=None, incognito_phone=None):
        break
    if schedule:
        await state.update_data(schedule_id=schedule.pk)
    else:
        await cb.message.answer('There is no record for this specialist, choose another one.',
                                reply_markup=m.get_specialist)
        # await asyncio.sleep(3)
        return

    await cb.message.answer('Date and time selection:', reply_markup=m.choose_datetime)
    await UserState.choice_datetime.set()
    await cb.answer()


# ЗДЕСЬ НАДО ВСТАВИТЬ ВЫБОР ИЗ КАЛЕНДАРЯ!
@dp.callback_query_handler(Text(['today', 'tomorrow']), state=UserState.choice_datetime)
async def set_datetime(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    payloads = await state.get_data()
    for message in payloads['messages_responses']:
        await message.delete()
    if cb.data=='today':
        date = datetime.now()
    if cb.data=='tomorrow':
        date = datetime.now() + timedelta(days=1)
    await state.update_data(date=date)
    client_id = await sync_to_async(funcs.get_client_id)(cb.from_user.username)
    if not client_id:
        # клиент зарегистрирован? проверка и далее - флаг и запрос номера телефона
        # если не зарегистрирован
        await state.update_data(client_id=None)
        payloads['messages_responses'].append(await cb.message.answer('We invite you to register in our database.'
                                                                      'Get a 5% discount.'))
        payloads['messages_responses'].append(await cb.message.answer('To register, read the consent '
                                                                      'for the processing of personal data.'))
        payloads['messages_responses'].append(await bot.send_document(chat_id=cb.from_user.id,
                                                                      document=open(Path(BASE_DIR, 'permitted.pdf'),
                                                                                    'rb'),
                                                                      reply_markup=m.accept_personal_data))
        await UserState.get_registration.set()
    else:
        await state.update_data(client_id=client_id)
        await state.update_data(incognito_phone=None)
        markup, dates = await sync_to_async(funcs.get_datetime)(date, payloads['specialist_id'])
        await state.update_data(dates=dates)
        await cb.message.answer('Possible time:', reply_markup=markup)
    await cb.answer()


@dp.callback_query_handler(Text(['personal_yes', 'personal_no']), state=UserState.get_registration)
async def accepting_permission(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.delete()
    payloads = await state.get_data()
    for message in payloads['messages_responses']:
        await message.delete()

    if cb.data == 'personal_no':
        registration_consent = False
        await cb.message.answer('Sorry. But we need your name and phone number to contact you.')
    else:
        registration_consent = True
    await state.update_data(registration_consent=registration_consent)
    await cb.message.answer('Enter your name:')
    await UserState.set_name_phone.set()
    await cb.answer()


@dp.message_handler(lambda msg: msg.text, state=UserState.set_name_phone)
async def set_name_phone(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer('Enter your phone number. The phone number must be entered in the format: "+99999999999". '
                     'Up to 15 digits are allowed.')
    await UserState.phone_verification.set()


@dp.message_handler(lambda msg: msg.text, state=UserState.phone_verification)
async def phone_verification(msg: types.Message, state: FSMContext):
    try:
        phone = PhoneNumber.from_string(msg.text, 'RU')
        phone_check = phone.is_valid()
    except NumberParseException:
        await msg.answer('The phone number was entered incorrectly! Try again.')
        return
    if not phone_check:
        await msg.answer('The phone number was entered incorrectly! Check the format. Try again.')
        return
    phone_as_e164 = phone.as_e164
    await msg.answer(f'The phone number is entered correctly! {phone_as_e164}')

    payloads = await state.get_data()
    incognito_phone = ''
    if payloads['registration_consent']:  # если дал согласие на регистрацию - сохранение юзера в БД
        client = await sync_to_async(funcs.registration_client)(payloads['name'], phone_as_e164,
                                                                msg.from_user.username, msg.from_user.id)
        await state.update_data(client_id=client.pk)
    else:
        incognito_phone = phone_as_e164
    await state.update_data(incognito_phone=incognito_phone)
    markup, dates = await sync_to_async(funcs.get_datetime)(payloads['date'], payloads['specialist_id'])
    await state.update_data(dates=dates)
    await msg.answer('Possible time:', reply_markup=markup)


async def record_save(state: FSMContext):

    # нужно из введенных пользователем даты и времени сделать проверку их наличия свободных в расписании и оттуда взять
    # chedule_id
    # schedule_id = 2  # временно
    #schedule_date = '2022-02-02'
    #schedule_time = '15:45'

    payloads = await state.get_data()
    tg_id = payloads['tg_id']
    client_id = payloads['client_id']
    #schedule_id = payloads['schedule_id']
    incognito_phone = payloads['incognito_phone']
    specialist_id = payloads['service_id']
    full_schedule_date = payloads['dates'][int(payloads['date_index'])]
    schedule_date = full_schedule_date.strftime('%m/%d/%Y')
    schedule_time = full_schedule_date.strftime('%H:%M')

    await sync_to_async(funcs.make_order)(full_schedule_date, specialist_id, client_id, payloads['service_id'], incognito_phone)
    await bot.send_message(tg_id, f'Thank you, you are signed up for the service "{payloads["service_name"]}" '                                  
                                  f'to a specialist {payloads["specialist_name"]}! \n'                       
                                  f'See you soon {schedule_date} в {schedule_time} at: '
                                  f'Moscow region, Balashikha, headquarters DEVMAN')
    await state.reset_state(with_data=False)
    await bot.send_message(tg_id, 'Main menu', reply_markup=m.client_start_markup)


# buy
#@dp.message_handler(Text(equals=['Buy'], ignore_case=True))
#async def payment(message: types.Message):
@dp.callback_query_handler(Text(['buy']), state=UserState.choice_datetime)
async def set_datetime(cb: types.CallbackQuery, state: FSMContext):
    if PAYMENT_TOKEN.split(':')[1] == 'TEST':
        await bot.send_message(cb.message.chat.id, 'Test payment!!!')

    price = types.LabeledPrice(label='test1', amount=300*100)
    await bot.send_invoice(cb.message.chat.id,
                           title='test2',
                           description='test2',
                           provider_token=PAYMENT_TOKEN,
                           currency='rub',
                           photo_url="https://www.aroged.com/wp-content/uploads/2022/06/Telegram-has-a-premium-subscription.jpg",
                           photo_width=416,
                           photo_height=234,
                           photo_size=416,
                           is_flexible=False,
                           prices=[price],
                           start_parameter='test2',
                           payload='test2')


# pre checkout (must be answered in 10 seconds)
@dp.pre_checkout_query_handler(lambda query: True, state=UserState.choice_datetime)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# successfull payment
@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT, state=UserState.choice_datetime)
async def successful_payment(message: types.Message):
    schedule_id = 29
    print('Successful_payment:')
    payment_info = message.successful_payment.to_python()
    for k, v in payment_info.items():
        print(f'{k} = {v}')

    await bot.send_message(message.chat.id,
                           f'Payment at {message.successful_payment.total_amount // 100} '
                           f'{message.successful_payment.currency} done')
    await sync_to_async(funcs.pay_order)(schedule_id)


#@dp.message_handler(Text(equals=['Calendar'], ignore_case=True))
#async def nav_cal_handler(message: Message):
@dp.callback_query_handler(Text(['calendar']), state=UserState.choice_datetime)
async def set_datetime(cb: types.CallbackQuery, state: FSMContext):    
    await cb.message.answer("Please select a date: ", reply_markup=await SimpleCalendar().start_calendar())


# simple calendar usage
@dp.callback_query_handler(simple_cal_callback.filter(), state=UserState.choice_datetime)
async def process_simple_calendar(cb: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(cb, callback_data)
    if selected:
        await cb.message.answer(
            f'You have chosen {date.strftime("%d/%m/%Y")}, choose a convenient time:',
        )
        payloads = await state.get_data()
        markup, dates = await sync_to_async(funcs.get_datetime)(date, payloads['specialist_id'])
        await state.update_data(dates=dates)
        await cb.message.answer('Possible time: ', reply_markup=markup)


@dp.callback_query_handler(Text(startswith='Possible'), state=UserState.choice_datetime)
async def set_time_window(cb: types.CallbackQuery, state: FSMContext):
    date_index = cb.data[15:]
    await state.update_data(date_index=date_index)
    await record_save(state)


@dp.callback_query_handler(Text(startswith='Possible'), state=UserState.phone_verification)
async def set_time_win(cb: types.CallbackQuery, state: FSMContext):
    date_index = cb.data[15:]
    await state.update_data(date_index=date_index)
    await record_save(state)


# видимо эти блоки ниже не понадобидись. Сделать запуск бота без on_startup
async def sentinel():
    while 1:
        logging.info('Какая то проверка в течении какого то периода')
        await asyncio.sleep(86400)


async def on_startup(_):
    asyncio.create_task(sentinel())

executor.start_polling(dp, skip_updates=False)
