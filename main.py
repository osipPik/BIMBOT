import datetime
import logging
import os
import secrets
import string
import telebot
from telebot import types
from pprint import pprint


from data_functions import get_data, InstructionCash, UnmarkedRequestCash,  MarkedRequestCash, SheetCash, \
    get_instruction, DataBaseFunctions, ImportFunction
from google_module import GoogleDocs, GoogleDocsRead, GoogleSheets, DictWorker
from recode_instriction_name import DecoderTableName

# Создается кэш дейсвтий пользователя
writer_data = UnmarkedRequestCash()
rating_data = MarkedRequestCash()
sheet_cash = SheetCash()
logger = telebot.logger

instruction_link_data = get_instruction('link', 'instruction')
instruction_link_list = [item[0] for item in instruction_link_data]
instruction_cash = InstructionCash()

instruction_cash.create_cash(instruction_link_list)


def dict_from_string(dict_in_string):
    first_list = str(dict_in_string).split(',')
    second_list = [tuple(str(item).split(':')) for item in first_list]
    third_list = [(key.replace(' ', '', 1), value.replace(' ', '', 1)) for key, value in second_list]
    dictionary = {key: value for key, value in third_list}
    return dictionary


HEROKU = os.environ.get('HEROKU')
if HEROKU == "True":
    TOKEN = os.environ.get('TOKEN')
    LINK_URL_SHEET = os.environ.get('LINK_URL_SHEET')
    KEY_USER_PARAM = os.environ.get('KEY_USER_PARAM')
    USER_BASE = os.environ.get('USER_BASE')
    KEY_INSTRUCT_PARAM = os.environ.get('KEY_INSTRUCT_PARAM')
    REQUEST_BASE = os.environ.get('REQUEST_BASE')
    DICTIONARY_INSTRUCT_REQUEST = dict_from_string(os.environ.get('DICTIONARY_INSTRUCT_REQUEST'))
    DICTIONARY_USER_REQUEST = dict_from_string(os.environ.get('DICTIONARY_USER_REQUEST'))
    REGISTRY_LINK = os.environ.get("REGISTRY_LINK")
    CASH_CAPACITY = os.environ.get("CASH_CAPACITY")
else:
    import config
    TOKEN = config.TOKEN
    LINK_URL_SHEET = config.LINK_URL_SHEETS
    KEY_USER_PARAM = config.KEY_USER_PARAM
    USER_BASE = config.USER_BASE
    KEY_INSTRUCT_PARAM = config.KEY_INSTRUCT_PARAM
    REQUEST_BASE = config.REQUEST_BASE
    DICTIONARY_INSTRUCT_REQUEST = dict_from_string(config.DICTIONARY_INSTRUCT_REQUEST)
    DICTIONARY_USER_REQUEST = dict_from_string(config.DICTIONARY_USER_REQUEST)
    REGISTRY_LINK = config.REGISTRY_LINK
    CASH_CAPACITY = config.CASH_CAPACITY

#sheet_values = GoogleSheets(REGISTRY_LINK).get_sheets_values('Реестр', start_row='2', end_column='DC')
#sheet_data_in_dict = DictWorker.generate_dict(keys=sheet_values[0], values=sheet_values[2:])
#filtered_data = DictWorker.filter_list_of_dicts('Статус', 'Разрешено', sheet_data_in_dict)

#sheet_cash.add_value(filtered_data)
sheet_data = GoogleSheets(LINK_URL_SHEET)
bot = telebot.TeleBot(TOKEN)


# это глвное меню бота (вызывается из базы данных, формируется на основе ее значений)
# функция заполняет клавиатуру которая генерируется из базы данных (только главное меню)
def get_date_time():
    offset = datetime.timedelta(hours=3)
    dt = datetime.datetime.now(tz=datetime.timezone(offset, 'МСК'))
    date = f'{dt.date().day}.{dt.date().month}.{dt.date().year}'
    time = f'{dt.time().hour}:{dt.time().minute}:{dt.time().second}'
    return date, time


class RequestToken:

    def __init__(self, length=16, token=''):
        self.length = length
        self.token = token

    def set_token(self):
        letters_and_digits = string.ascii_letters + string.digits
        self.token = ''.join(secrets.choice(
            letters_and_digits) for _ in range(self.length))
        print("ID обращения", self.length, "символов:", self.token)

    def refresh_token(self):
        self.set_token()

import_user_token = RequestToken()
import_user_token.set_token()
import_request_token = RequestToken()
import_request_token.set_token()


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, "Доступные команды бота:\n/start - запуск бота\n/restart - перезапуск бота")


@bot.message_handler(commands=['start'])
def start(message):
    instruction_token = RequestToken()
    instruction_token.set_token()
    set_job_email(message, instruction_token)


@bot.message_handler(commands=['restart'])
def reload_bot(message):
    instruction_token = RequestToken()
    try:
        writer_data.write_values('requests', max_count_element=int(CASH_CAPACITY))
        rating_data.update_instruction_rating(max_count_element=int(CASH_CAPACITY))
        instruction_token.refresh_token()
    except Exception as e:
        print(f"Data wasn't writen, error: {e}")
    set_job_email(message, instruction_token)


def set_job_email(message, instruction_token):
    user_data = DataBaseFunctions.select_data('users')
    id_list = [item[0] for item in user_data]

    if str(message.chat.id) not in id_list:
        print("Пользователь не найден")
        markup = types.ReplyKeyboardRemove()
        msg = bot.send_message(message.chat.id, "Введите рабочую почту", reply_markup=markup, disable_notification=True)
        bot.register_next_step_handler(msg, add_user_in_base, instruction_token)

    else:
        print("Пользователь найден")
        main_menu_select_step(message, instruction_token)


def add_user_in_base(message, instruction_token):
    if "@pik.ru" in message.text:
        bot.send_message(message.chat.id, "Данные записываются...")
        try:
            if message.chat.username:
                user_name = message.chat.username
            else:
                user_name = 'Empty'
            DataBaseFunctions.insert_user((message.chat.id, user_name, message.text, "Не проверен"), 'users')
            main_menu_select_step(message, instruction_token)
        except Exception as e:
            print(f"Пользователь не записан. ошибка {e}")
            bot.send_message(message.chat.id, "Данные не записаны")
            set_job_email(message, instruction_token)
    else:
        bot.send_message(message.chat.id, "Почта не зарегистрирована в домене pik.ru")
        set_job_email(message, instruction_token)


def main_menu_select_step(message, instruction_token):
    data = get_data('t1')
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    message_list = []
    for item in data:
        if item[1] != "" and item[2] is not None and item[2] != "":

            item_btn = types.KeyboardButton(item[1])
            markup.add(item_btn)
        message_list.append(str(item[4]))
    if str(message.chat.id) in ['415374544', '300855004']:
        markup.add(f"Импортировать данные запросов: {import_request_token.token}")
        markup.add(f'Импортировать данные пользователей: {import_user_token.token}')
    msg = bot.send_message(message.chat.id,
                           message_list[0],
                           reply_markup=markup, disable_notification=True)  # вызвать клаву
    bot.register_next_step_handler(msg, process_select_step, data, 't1', instruction_token)


# выбор дальнейших шагов в по таблицам БД
def process_select_step(message, data, selected_table, instruction_token):
    # пустые массивы в начале функций нужны для того что при каждом вызове функции из значения заполнялись заново
    next_step = []
    texts = []
    last_step = []

    try:
        for item in data:  # пробег по массиву из кортежей, получаем следующую т
            # аблицу, текст кнопок, и предыдущую таблицу
            texts.append(item[1])
            next_step.append(str(item[2]))
            last_step.append(str(item[3]))
            print(item[1], "->", item[2])
        index = texts.index(message.text)
        table = next_step[index]
        last_table = last_step[index]
        print("Переход к финальной инструкции IT", str("t01" in next_step))
        print("Переход к финальной инструкции BIM", str("t02" in next_step))
        if "t01" in next_step or "t02" in next_step or "t1" in next_step:  # если следующая таблица пустая то вызывается
            # функция в которой выводится текст инструкции
            instruction_list = []
            for item in data:
                instruction_list.append(item[5])
            index = texts.index(message.text)
            instruction = instruction_list[index]
            table = next_step[index]
            if next_step[index] == '<-':
                data = get_data(last_table)
                menu_select_step(message, data, last_table, instruction_token)
            else:
                if next_step[index] == 't1':
                    case = 1
                elif next_step[index] == 't01' or next_step[index] == 't02':
                    case = 2
                else:
                    case = 3
                data = get_data(table)
                if case == 3:
                    print_instruction_step(message, instruction, data, case, table, instruction_token)
                else:
                    print_instruction_step(message, instruction, data, case, selected_table, instruction_token)

        else:  # в любом другом случае получаем данные о дальнейшем и предыдущем шаге
            # для вызова шаблонной функции генерации кнопок
            print(table)
            if table == "<-":
                data = get_data(last_table)
                menu_select_step(message, data, table, instruction_token)
            else:
                data = get_data(table)
                menu_select_step(message, data, table, instruction_token)
    except Exception as e:
        if message.text == "В НАЧАЛО":
            reload_bot(message)
        elif message.text == "/start":
            start(message)
        elif message.text == '/restart':
            reload_bot(message)
        elif message.text == f"Импортировать данные запросов: {import_request_token.token}":
            ImportFunction.import_in_google_sheet(LINK_URL_SHEET, 'База обращений', 'requests')
            reload_bot(message)
        elif message.text == f'Импортировать данные пользователей: {import_user_token.token}':
            ImportFunction.import_user_in_google_sheet(LINK_URL_SHEET, 'База пользователей', 'users')
            reload_bot(message)
        else:
            print(str(e))
            bot.reply_to(message, "Раздел")
            bot.send_message(message.chat.id, 'В данный момент не доступен', reply_markup=types.ReplyKeyboardRemove(),
                             disable_notification=True)
            reload_bot(message)

# Обычная функция генерации кнопок, ничего примечательного


def menu_select_step(message, data, table, instruction_token):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    message_list = []
    for item in data:
        if item[1] != "" and item[2] is not None and item[2] != "":
            itembtn = types.KeyboardButton(item[1])
            markup.add(itembtn)
        message_list.append(str(item[4]))
    item_btn_back = types.KeyboardButton('В НАЧАЛО')
    markup.add(item_btn_back)
    msg = bot.send_message(message.chat.id,
                           message_list[0],
                           reply_markup=markup, disable_notification=True)  # вызвать клаву
    bot.register_next_step_handler(msg, process_select_step, data, table, instruction_token)

# функция отвечает за вывод текста(далее изображений) инструкции


def print_instruction_step(message, instruction, data, case, selected_table, instruction_token):
    data = data
    print(selected_table)

    if case == 3:
        instruction_name = DecoderTableName.decode_text(selected_table)
    else:
        instruction_name = DecoderTableName.decode_text(selected_table) + f'->{message.text}'

    data_list = (instruction_token.token, str(message.chat.id), instruction_name, message.text, get_date_time()[0],
               get_date_time()[1], "Без оценки")
    full_data = instruction_token.token, data_list

    if instruction != "":


        if message.text != "Спасибо, инструкция помогла" and message.text != "Инструкция не помогла":
            pass
            #insert_data(values)

        if 'https://docs.google.com/' in instruction:
            writer_data.add_value(full_data)
            pprint(writer_data.values)
            print(len(writer_data.values))
            index = instruction_link_list.index(instruction)
            instruction_list = instruction_cash.values[index]

            for i, item in enumerate(instruction_list):
                if item.count('googleusercontent') == 0:
                    bot.send_message(message.chat.id, instruction_list[i], disable_notification=True, parse_mode="HTML")
                else:
                    try:
                        bot.send_photo(message.chat.id, instruction_list[i], disable_notification=True)
                    except Exception as e:
                        print("%s: %s" % (type(e), e))
                        instruction_cash.update_cash_unit(index, instruction_link_list)
                        instruction_list = instruction_cash.values[index]
                        bot.send_photo(message.chat.id, instruction_list[i], disable_notification=True)
        else:
            bot.send_message(message.chat.id, instruction, disable_notification=True, parse_mode="HTML")

    data_lists = [[item[0], [val for val in item[1]]] for item in writer_data.values]
    if case == 1:
        if message.text == "Спасибо, инструкция помогла":
            rating = 'Положительная'
        else:
            rating = 'Отрицательная'

        for index, item in enumerate(writer_data.values):
            print(instruction_token.token in item[0])
            if instruction_token.token in item[0]:
                data_lists[index][1][6] = rating
                rating_data.add_value(data_lists[index])
            print(len(rating_data.values))

        reload_bot(message)

    elif case == 2:
        final_menu_select_step(message, data, instruction_token)

    elif case == 3:
        if message.text != 'Текст':
            for index, item in enumerate(writer_data.values):
                print(instruction_token.token in item[0])
                if instruction_token.token in item[0]:
                    data_lists[index][1][6] = 'Отрицательная'
                    rating_data.add_value(data_lists[index])
                print(len(rating_data.values))
            instruction_token.refresh_token()
        menu_select_step(message, data, selected_table, instruction_token)


# Последний шаг, генерируются кнопки для завершения работы (вопрос: помогло или нет?)
def final_menu_select_step(message, data, instruction_token):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    message_list = []
    for item in data:
        itembtn = types.KeyboardButton(item[1])
        message_list.append(str(item[2]))
        markup.add(itembtn)
    msg = bot.send_message(message.chat.id,
                           message_list[0],
                           reply_markup=markup, disable_notification=True)  # вызвать клаву
    bot.register_next_step_handler(msg, final_process_select_step, data, instruction_token)


# выводится тескт с дальнейшими указаниями если инструкция не помогла. (в дальнейшем здесь будет вызываться запись в БД)
def final_process_select_step(message, data, instruction_token):
    texts = []
    answers = []
    try:
        for item in data:
            texts.append(item[1])
            answers.append(item[3])
        index_answer = texts.index(message.text)
        if message.text == "Да":
            rating = 'Положительная'
        else:
            rating = 'Отрицательная'

        data_lists = [[item[0], [val for val in item[1]]] for item in writer_data.values]
        for index, item in enumerate(writer_data.values):
            print(instruction_token.token in item[0])
            if instruction_token.token in item[0]:
                data_lists[index][1][6] = rating
                rating_data.add_value(data_lists[index])
                print(len(rating_data.values))

        pprint(rating_data.values)
        bot.send_message(message.chat.id, answers[index_answer], disable_notification=True)
        reload_bot(message)
    except Exception as e:
        if message.text == "В НАЧАЛО":
            reload_bot(message)
        else:
            print(str(e))
            bot.reply_to(message, 'Такого раздела пока нет')
            reload_bot(message)


@bot.message_handler(content_types=['text'])
def send_warning(message):
    bot.send_message(message.chat.id, 'Что-то пошло не так, бот на вашем устройстве не активен, '
                                      'выберите команду /restart для повторного перезапуска бота')

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except:
        pass

