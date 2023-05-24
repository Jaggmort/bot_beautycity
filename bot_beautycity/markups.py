from aiogram import types
from admin_beautycity.models import Service


# ======= CLIENT BLOCK (START) ==============================================================================
client_start_markup = types.InlineKeyboardMarkup(row_width=2)
client_start_markup_buttons = [
    types.InlineKeyboardButton('О нас', url='https://telegra.ph/O-salonah-krasoty-BeautyCity-05-23'),
    types.InlineKeyboardButton('Записаться на услугу', callback_data='get_service'),
    types.InlineKeyboardButton('Позвонить нам', callback_data='call_to_us'),
]
client_start_markup.add(*client_start_markup_buttons)

get_service = types.InlineKeyboardMarkup(row_width=3)
services = Service.objects.all()
get_service_buttons = []
for service in services:
    get_service_buttons.append(types.InlineKeyboardButton(service.service_name, callback_data=service.service_english))
get_service_buttons.append(types.InlineKeyboardButton('Позвонить нам', callback_data='call_to_us'))
get_service_buttons.append(types.InlineKeyboardButton('<= Вернуться', callback_data='exit'))
get_service.add(*get_service_buttons)


# здесь необходимо реализовать выбор даты-времени из какого то массива рабочего времени.
choose_datetime = types.InlineKeyboardMarkup(row_width=2)
choose_datetime_buttons = [
    types.InlineKeyboardButton('Сегодня', callback_data='today'),
    types.InlineKeyboardButton('Завтра', callback_data='tomorrow'),
    types.InlineKeyboardButton('Позвонить нам', callback_data='call_to_us'),
    types.InlineKeyboardButton('<= Вернуться', callback_data='exit'),
]
choose_datetime.add(*choose_datetime_buttons)

make_order = types.InlineKeyboardMarkup(row_width=2)
make_order_buttons = [
    types.InlineKeyboardButton('Записаться', callback_data='order_yes'),
    types.InlineKeyboardButton('Отказаться', callback_data='order_no'),
    types.InlineKeyboardButton('Позвонить нам', callback_data='call_to_us'),
    types.InlineKeyboardButton('<= Вернуться', callback_data='exit'),
]
make_order.add(*make_order_buttons)

accept_personal_data = types.InlineKeyboardMarkup(row_width=2)
accept_personal_data_buttons = [
    types.InlineKeyboardButton('Согласен', callback_data='personal_yes'),
    types.InlineKeyboardButton('Несогласен', callback_data='personal_no'),
    types.InlineKeyboardButton('Позвонить нам', callback_data='call_to_us'),
    types.InlineKeyboardButton('<= Вернуться', callback_data='exit'),
]
accept_personal_data.add(*accept_personal_data_buttons)

exit_markup = types.InlineKeyboardMarkup(row_width=1)
exit_markup_btn = types.InlineKeyboardButton('<= Вернуться', callback_data='exit')
exit_markup.add(exit_markup_btn)


# ======= CLIENT BLOCK (END) ===============================================================================
