import logging
import os
import sys
import wave
from datetime import datetime
from tinkoff_voicekit_client import ClientSTT
import psycopg2
import jsonschema.exceptions as exceptions_js
import grpc._channel as exceptions_grpc


API_KEY = 'API_KEY'
SECRET_KEY = 'SECRET_KEY'
LOG_FILE_INFO = 'LOG_FILE_INFO'   # Имя логфайла
LOG_FILE_ERROR = 'LOG_FILE_ERROR'   # Имя логфайла для ошибок

counter_id = 0


def glob_id():
    """ Функция, которая увеличивает id. Нужна для уникальности id в процессе работы программы """
    global counter_id
    counter_id += 1


# Подключение к базе данных Postgres
connection = psycopg2.connect(database='postgres', user='postgres', password='password', host='host')
cursor = connection.cursor()

# Подключение и настройка формата для обычного логфайла
logger_info = logging.getLogger('logger_info')
log_formatter = logging.Formatter('%(message)s')
file_handler_info = logging.FileHandler(LOG_FILE_INFO, mode='a')
file_handler_info.setFormatter(log_formatter)
file_handler_info.setLevel(logging.INFO)
logger_info.addHandler(file_handler_info)
logger_info.setLevel(logging.INFO)

# Подключение и настройка формата для логфайла с ошибками
logger_error = logging.getLogger('logger_error')
log_formatter = logging.Formatter('%(message)s')
file_handler_error = logging.FileHandler(LOG_FILE_ERROR, mode='a')
file_handler_error.setFormatter(log_formatter)
file_handler_error.setLevel(logging.ERROR)
logger_error.addHandler(file_handler_error)
logger_error.setLevel(logging.ERROR)


def log_info(text):
    """ Функция, которая делает запись в логфайл """
    logger_info.info(text)
    print(text)


def log_error(text):
    """ Функция, которая делает запись в логфайл для ошибок """
    date = datetime.now().date()
    time = datetime.now().time().strftime("%H:%M:%S")
    logger_error.error(f'{date},{time},{text}')
    print(text)


def database_init():
    """" Функция, создающая таблицу, если ее еще нет """
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS VOICEKIT_DATABASE
             (DATE DATE NOT NULL,
             TIME TIME NOT NULL,
             ID INT NOT NULL,
             RESULT TEXT NOT NULL,
             PHONE TEXT NOT NULL,
             LENGTH FLOAT NOT NULL,
             RESULT_TEXT TEXT NOT NULL);''')
    except:
        log_error('Database init error')
    connection.commit()


def database_add(*args):
    """ Функция, делающая запись в таблицу """
    try:
        cursor.execute('''INSERT INTO VOICEKIT_DATABASE(DATE, TIME, ID, RESULT, PHONE, LENGTH, RESULT_TEXT) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)''', args)
    except:
        log_error('Database add error')
    connection.commit()


def rec_stage_processing(**kwargs):
    """ Функция, которая выясняет результат, делает запись в логфайл и в базу данных """

    # Берем данные из kwargs
    text = kwargs.get("text")
    phone_number = kwargs.get("phone_number")
    rec_stage = kwargs.get("rec_stage")
    db_flag = kwargs.get("db_flag")

    # Считает длину .wav файла. Для этого считаем кол-во кадров и частоту кадров, делим первое на второе.
    with wave.open(filePath, 'r') as f:
        frames = f.getnframes()
        rate = f.getframerate()
        length = frames / rate

    # Вычисляем дату и время без микросекунд.
    date = datetime.now().date()
    time = datetime.now().time().strftime("%H:%M:%S")

    # Увеличиваем id.
    glob_id()

    # Вычисляем результат распознования
    rez = 'noresult'
    if rec_stage == 1:
        if 'автоответчик' in text:
            rez = 'АО'
        elif 'человек' in text:
            rez = 'человек'
    elif rec_stage == 2:
        if text.find('нет') != -1 or text.find('неудобно') != -1:
            rez = 'отрицательно'
        elif text.find('говорите') != -1 or text.find('да конечно') != -1 or text.find('да') != -1:
            rez = 'положительно'

    # Проверяем, есть ли у нас пустые данные
    try:
        for i in [date, time, counter_id, rez, phone_number, length, text]:
            if i == '':
                raise IndexError
    except IndexError:
        log_error('Parameters can not be empty')
        sys.exit(-1)

    # Делаем запись в логфайл
    logger_info.info(f'{date},{time},{counter_id},{rez},{phone_number},{length},{text}')

    # Если есть соответствующий флаг, делаем запись в базу данных
    if db_flag:
        database_add(date, time, counter_id, rez, phone_number, length, text)

    if rez == 'АО' or 'отрицательно':
        return 0
    if rez == 'человек' or 'положительно':
        return 1

    return -1


def audio_recognition(**kwargs):
    """ Основная функция """
    client = ClientSTT(API_KEY, SECRET_KEY)
    audio_config = {
        "encoding": "LINEAR16",
        "sample_rate_hertz": 8000,
        "num_channels": 1
    }
    file_path = kwargs.get("filePath")

    try:
        response = client.recognize(file_path, audio_config)
    except ValueError:   # Проверка на правильность пути файла
        log_error('Your file path is wrong')
        sys.exit(-1)
    except exceptions_js.ValidationError:   # Проверка на правильность настроек
        log_error('Your audio config is wrong')
        sys.exit(-1)
    except exceptions_grpc._InactiveRpcError:   # Проверка на правильность API_KEY и SECRET_KEY
        log_error('Your API_KEY or SECRET_KEY is wrong')
        sys.exit(-1)

    # Достаем результат распознования из ответа
    text = response[0]['alternatives'][0]['transcript']
    rec_stage_processing(rec_stage=kwargs.get("recStage"), text=text,
                         phone_number=kwargs.get("phoneNumber"), db_flag=kwargs.get("dbFlag"))


# Основной код программы
if __name__ == '__main__':

    flag = 1
    filePath = None
    while flag == 1:
        filePath = input('Input path: ')
        phoneNumber = input('Input phone number: ')
        try:
            dbFlag = int(input('Input flag of writing to the database(0 or 1): '))
            recStage = int(input('Input recognition stage(1 or 2): '))
            if (dbFlag not in [0, 1]) or (recStage not in [1, 2]):
                raise ValueError
        except ValueError:
            log_error('dbFlag must be equal to 0 or 1 and recStage must be equal to 1 or 2')
            sys.exit(-1)

        database_init()   # Создание таблицы базы данных, если ее еще не существует.
        audio_recognition(filePath=filePath, phoneNumber=phoneNumber, dbFlag=dbFlag, recStage=recStage)   # Основная функция
        flag = int(input('Input flag(1 to continue): '))

    connection.close()   # Закрытие соединения с базой данных
    if filePath is not None:
        os.remove(filePath)   # Удаление файла

