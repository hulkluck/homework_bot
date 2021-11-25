import logging
import os
import time

import dotenv
import requests
import telegram

dotenv.load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            f'Сообщение "{message}" для "{TELEGRAM_CHAT_ID}" отправлено')
    except Exception as error:
        logging.error(f'Сообщение "{message}" для'
                      f'"{TELEGRAM_CHAT_ID}" Сообшение не отправлено. Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Запрос к API"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logging.error(
                f'practicum.yandex.ru != 200: {response.status_code}')
            raise Exception('practicum.yandex.ru != 200')
        return response.json()
    except response.RequestException as error:
        logging.warning(f'проблема с Яндекс API! {error}')
        raise response.Exception('PRACTICUM ответ не 200')


def check_response(response):
    """проверяет API ответ на соответствие."""
    if not isinstance(response['homeworks'], list):
        logging.error('В ответе homeworks не список list')
        raise Exception('В ответе homeworks не список list')
    if response['homeworks'] is None:
        logging.error('Нет списка list в ответе homeworks')
        raise Exception('Нет списка list в ответе homeworks')
    return response['homeworks']


def parse_status(homework):
    """Проверка статуса"""
    name_homework = homework.get('homework_name')
    status_homework = homework.get('status')
    if status_homework is None:
        logging.error('parse_status - нет status')
        raise Exception('parse_status -нет status')
    if status_homework not in HOMEWORK_STATUSES:
        logging.error('homework_status - не корректный')
        raise KeyError('homework_status - не корректный')
    verdict = HOMEWORK_STATUSES[status_homework]
    return f'Изменился статус проверки работы "{name_homework}". {verdict}'


def check_tokens():
    """Проверка наличия токенов"""
    tokens = True
    if PRACTICUM_TOKEN is None:
        error_text = 'Ошибка, отсутствует PRACTICUM_TOKEN'
        logging.critical(error_text)
        tokens = False
    elif TELEGRAM_TOKEN is None:
        logging.critical('Ошибка, отсутствует TELEGRAM_TOKEN')
        tokens = False
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('Ошибка, отсутствует TELEGRAM_CHAT_ID')
        tokens = False
    return tokens


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        send_message(bot, 'Критическая ошибка,'
                     'отсутствует токен, бот остановлен')
        exit()
    errors = True
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if not response.get('homeworks'):
                time.sleep(RETRY_TIME)
                continue
            if check_response(response):
                homework = response.get('homeworks')[0]
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')
            logging.info('Нет изменений, ждем')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logging.error(message, exc_info=True)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
