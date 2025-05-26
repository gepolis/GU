import json

import requests


def create_crystalpay_invoice(amount, description=None, email=None, extra_data=None):
    """
    Создание платежного инвойса в CrystalPay

    :param amount: Сумма платежа
    :param description: Описание платежа (опционально)
    :param email: Email плательщика (опционально)
    :param extra_data: Дополнительные данные (опционально)
    :return: Ответ API или None в случае ошибки
    """
    # Конфигурация
    API_URL = "https://api.crystalpay.io/v3/invoice/create/"
    AUTH_LOGIN = "gu"  # Ваш логин кассы
    SECRET_KEY = "87ca148ed9581a81c440ed58766f0b3944ad9367"  # Ваш секретный ключ

    # Подготовка данных запроса
    payload = {
        "auth_login": AUTH_LOGIN,
        "auth_secret": SECRET_KEY,
        "amount": amount,
        "type": "topup",  # Тип инвойса (пополнение)
        "lifetime": 30,  # Время жизни инвойса в минутах (30 мин)
        "amount_currency": "RUB",  # Валюта (рубли)
        "description": description,
        "payer_details": email,
        "extra": extra_data,
    }

    # Удаляем None-значения
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        # Отправка запроса
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()  # Проверка на ошибки HTTP

        # Парсинг ответа
        result = response.json()

        if not result.get('error'):
            return result
        else:
            return None

    except requests.exceptions.RequestException as e:
        return None
    except json.JSONDecodeError:
        return None


def get_invoice_info(invoice_id):
    """
    Получение информации о инвойсе в CrystalPay

    :param invoice_id: ID инвойса (например "123456789_abcdefghij")
    :return: Ответ API или None в случае ошибки
    """
    # Конфигурация
    API_URL = "https://api.crystalpay.io/v3/invoice/info/"
    AUTH_LOGIN = "gu"  # Ваш логин кассы
    SECRET_KEY = "87ca148ed9581a81c440ed58766f0b3944ad9367"  # Ваш секретный ключ

    # Подготовка данных запроса
    payload = {
        "auth_login": AUTH_LOGIN,
        "auth_secret": SECRET_KEY,
        "id": invoice_id
    }

    try:
        # Отправка запроса
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()  # Проверка на ошибки HTTP

        # Парсинг ответа
        result = response.json()

        if not result.get('error'):
            print("Информация об инвойсе получена успешно!")
            print(f"Статус: {result['state']}")
            print(f"Сумма: {result['rub_amount']} RUB")
            print(f"Создан: {result['created_at']}")
            print(f"Истекает: {result['expired_at']}")
            return result
        else:
            print("Ошибка при получении информации об инвойсе:")
            print(result.get('errors', 'Неизвестная ошибка'))
            return None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка соединения с API: {e}")
        return None
    except json.JSONDecodeError:
        print("Ошибка обработки ответа сервера")
        return None